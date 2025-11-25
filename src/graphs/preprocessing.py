"""LangGraph workflow that prepares checker prompts per rubric subtopic."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

try:
    import yaml
except ImportError:  # pragma: no cover - fallback when PyYAML unavailable
    yaml = None
from langgraph.graph import END, START, StateGraph

from src.core.preprocessing_state import (
    ExerciseRubric,
    PreprocessingState,
    ReferenceSolution,
    ReferenceSolutionInput,
    RubricSubtopic,
    SubtopicPrompt,
)


def _load_file_text(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Reference solution not found: {file_path}")
    return path.read_text(encoding="utf-8")


def load_rubric_file(state: PreprocessingState) -> PreprocessingState:
    """Node: parse the exercise-specific rubric YAML."""
    rubric_path = state.get("rubric_path")
    if not rubric_path:
        raise ValueError("rubric_path is required in the preprocessing state.")

    rubric_text = Path(rubric_path).read_text(encoding="utf-8")
    rubric = (
        yaml.safe_load(rubric_text)
        if yaml is not None
        else _fallback_parse_rubric(rubric_text)
    )
    exercises = rubric.get("exercises", [])
    if not exercises:
        raise ValueError("rubric must include an 'exercises' list.")

    exercise_rubrics: Dict[str, ExerciseRubric] = {}

    for exercise in exercises:
        exercise_id = exercise.get("id")
        if not exercise_id:
            raise ValueError("Each exercise in the rubric must have an id.")
        exercise_type = exercise.get("type", "regular")

        if exercise_type == "debug":
            exercise_rubrics[exercise_id] = ExerciseRubric(
                exercise_id=exercise_id,
                type="debug",
                fixes=list(exercise.get("fixes", [])),
            )
            continue

        raw_subtopics = exercise.get("subtopics", [])[:4]
        if len(raw_subtopics) < 1:
            raise ValueError(f"Exercise {exercise_id} is missing subtopics.")

        normalized_subtopics: List[RubricSubtopic] = []
        for subtopic in raw_subtopics:
            sub_id = subtopic.get("id")
            topic_name = subtopic.get("topic", "Unnamed Topic")
            text = subtopic.get("text", "").strip()
            if not sub_id or not text:
                raise ValueError(
                    f"Exercise {exercise_id} has an invalid subtopic entry."
                )
            compound_id = f"{exercise_id}:{sub_id}"
            normalized = RubricSubtopic(
                subtopic_id=compound_id,
                topic_id=sub_id,
                topic_name=topic_name,
                text=text,
            )
            normalized_subtopics.append(normalized)

        exercise_rubrics[exercise_id] = ExerciseRubric(
            exercise_id=exercise_id,
            type="regular",
            subtopics=normalized_subtopics,
        )

    state["rubric"] = rubric
    state["exercise_rubrics"] = exercise_rubrics
    return state


def normalize_reference_code(state: PreprocessingState) -> PreprocessingState:
    """Node: normalize line endings for reference solutions."""
    references = state.get("reference_solutions")
    if not references:
        raise ValueError("reference_solutions must be provided.")
    debug_exercises = set(state.get("debug_exercises") or [])

    normalized: List[ReferenceSolution] = []
    for reference in references:
        solution_id = reference.get("solution_id")
        if not solution_id:
            raise ValueError("Each reference solution must have a solution_id.")

        code = reference.get("code")
        source_path = reference.get("path")
        if code is None:
            if not source_path:
                raise ValueError(
                    f"Reference {solution_id} must include either 'code' or 'path'."
                )
            code = _load_file_text(source_path)

        normalized_code = (
            code.replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"
        )
        filename = reference.get("filename")
        if not filename and source_path:
            filename = Path(source_path).name
        filename = filename or solution_id
        is_debug = bool(reference.get("is_debug") or solution_id in debug_exercises)

        normalized.append(
            ReferenceSolution(
                solution_id=solution_id,
                code=normalized_code,
                filename=filename,
                source_path=source_path,
                is_debug=is_debug,
            )
        )

    state["normalized_reference_solutions"] = normalized
    return state


def _build_checker_prompt(
    subtopic: RubricSubtopic,
    reference: ReferenceSolution,
) -> str:
    """Create the textual instructions used by downstream checkers."""
    topic_name = subtopic["topic_name"]
    requirement = subtopic["text"]
    reference_label = reference["filename"]
    reference_code = reference["code"]

    prompt = f"""You are grading a single rubric subtopic for a C assignment.

Topic: {topic_name}
Requirement: {requirement}

Instructions:
1. Check ONLY this subtopic. Ignore every other rubric requirement.
2. Compare the student submission to the official reference solution to understand the intended behavior.
3. Focus strictly on whether the student's code satisfies the requirement above.
4. Do not evaluate style or correctness outside this subtopic.

Official reference solution ({reference_label}):
```
{reference_code}
```

When you later receive a student submission, decide PASS or FAIL for this subtopic and explain briefly.
"""
    return prompt


def _build_debug_prompt(
    exercise_id: str, fixes: List[str], reference: ReferenceSolution
) -> str:
    """Create a single prompt that checks all required debug fixes."""
    fixes_text = "\n".join(f"{idx + 1}. {fix}" for idx, fix in enumerate(fixes))
    reference_label = reference["filename"]
    reference_code = reference["code"]

    prompt = f"""You are grading a debug exercise. Verify that ALL required fixes are implemented.

Exercise: {exercise_id}
Required fixes:
{fixes_text}

Instructions:
1. Check ONLY whether the student's code implements every required fix above.
2. Compare to the official reference solution to understand the intended behavior.
3. Ignore unrelated style or requirements.

Official reference solution ({reference_label}):
```
{reference_code}
```

When you later receive a student submission, decide PASS or FAIL for this debug exercise and explain briefly."""
    return prompt


def build_subtopic_prompts(state: PreprocessingState) -> PreprocessingState:
    """Node: build prompts for each exercise."""
    exercise_rubrics = state.get("exercise_rubrics") or {}
    references = state.get("normalized_reference_solutions") or []
    if not exercise_rubrics:
        raise ValueError("No exercise rubrics were loaded from the rubric.")
    if not references:
        raise ValueError("No reference solutions are available.")

    prompts: Dict[str, Dict[str, SubtopicPrompt]] = {}
    prompts_by_exercise: Dict[str, Dict[str, SubtopicPrompt]] = {}

    for reference in references:
        exercise_id = reference["solution_id"]
        exercise_rubric = exercise_rubrics.get(exercise_id)
        if not exercise_rubric:
            continue

        if exercise_rubric.get("type") == "debug":
            fixes = exercise_rubric.get("fixes") or []
            checker_prompt = _build_debug_prompt(exercise_id, fixes, reference)
            subtopic_id = f"{exercise_id}:debug"
            prompt_entry = SubtopicPrompt(
                subtopic_id=subtopic_id,
                topic_name="Debug Fixes",
                rubric_text="\n".join(fixes),
                reference_solution_id=exercise_id,
                reference_filename=reference["filename"],
                checker_prompt=checker_prompt,
            )
            prompts.setdefault(subtopic_id, {})[exercise_id] = prompt_entry
            prompts_by_exercise[exercise_id] = {subtopic_id: prompt_entry}
            continue

        subtopics = exercise_rubric.get("subtopics") or []
        prompts_by_exercise[exercise_id] = {}
        for subtopic in subtopics[:4]:
            subtopic_id = subtopic["subtopic_id"]
            checker_prompt = _build_checker_prompt(subtopic, reference)
            prompt_entry = SubtopicPrompt(
                subtopic_id=subtopic_id,
                topic_name=subtopic["topic_name"],
                rubric_text=subtopic["text"],
                reference_solution_id=exercise_id,
                reference_filename=reference["filename"],
                checker_prompt=checker_prompt,
            )
            prompts.setdefault(subtopic_id, {})[exercise_id] = prompt_entry
            prompts_by_exercise[exercise_id][subtopic_id] = prompt_entry

    state["prompts_by_subtopic"] = prompts
    state["prompts_by_exercise"] = prompts_by_exercise
    return state


def build_preprocessing_graph() -> StateGraph:
    """Assemble the preprocessing LangGraph."""
    workflow = StateGraph(PreprocessingState)
    workflow.add_node("load_rubric_file", load_rubric_file)
    workflow.add_node("normalize_reference_code", normalize_reference_code)
    workflow.add_node("build_subtopic_prompts", build_subtopic_prompts)

    workflow.add_edge(START, "load_rubric_file")
    workflow.add_edge("load_rubric_file", "normalize_reference_code")
    workflow.add_edge("normalize_reference_code", "build_subtopic_prompts")
    workflow.add_edge("build_subtopic_prompts", END)

    return workflow


preprocessing_graph = build_preprocessing_graph().compile()

__all__ = ["preprocessing_graph", "build_preprocessing_graph"]


# ---------------------------------------------------------------------------
# Fallback parsing utilities
# ---------------------------------------------------------------------------


def _fallback_parse_rubric(rubric_text: str) -> Dict:
    """Parse the rubric when PyYAML is unavailable."""
    import json

    try:
        return json.loads(rubric_text)
    except Exception as exc:  # pragma: no cover - best-effort fallback
        raise ValueError(
            "Failed to parse rubric without PyYAML; please install PyYAML."
        ) from exc
