"""LangGraph workflow that prepares checker prompts per rubric subtopic."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover - fallback when PyYAML unavailable
    yaml = None
from langgraph.graph import END, START, StateGraph

from src.core.preprocessing_state import (
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
    """Node: parse the rubric YAML and flatten subtopics."""
    rubric_path = state.get("rubric_path")
    if not rubric_path:
        raise ValueError("rubric_path is required in the preprocessing state.")

    rubric_text = Path(rubric_path).read_text(encoding="utf-8")
    rubric = (
        yaml.safe_load(rubric_text)
        if yaml is not None
        else _fallback_parse_rubric(rubric_text)
    )
    topics = rubric.get("topics", [])

    subtopics: List[RubricSubtopic] = []
    for topic in topics:
        topic_id = topic.get("id")
        topic_name = topic.get("name", "Unnamed Topic")
        for subtopic in topic.get("subtopics", []):
            subtopics.append(
                RubricSubtopic(
                    subtopic_id=subtopic["id"],
                    topic_id=topic_id,
                    topic_name=topic_name,
                    text=subtopic["text"],
                )
            )

    state["rubric"] = rubric
    state["subtopics"] = subtopics
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
    state["debug_reference_ids"] = [
        ref["solution_id"] for ref in normalized if ref["is_debug"]
    ]
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


def build_subtopic_prompts(state: PreprocessingState) -> PreprocessingState:
    """Node: build prompts for each (subtopic, reference) pair."""
    subtopics = state.get("subtopics") or []
    references = state.get("normalized_reference_solutions") or []
    if not subtopics:
        raise ValueError("No subtopics were loaded from the rubric.")
    if not references:
        raise ValueError("No reference solutions are available.")

    prompts: Dict[str, Dict[str, SubtopicPrompt]] = {}
    prompts_by_exercise: Dict[str, Dict[str, SubtopicPrompt]] = {}
    for subtopic in subtopics:
        subtopic_id = subtopic["subtopic_id"]
        prompts[subtopic_id] = {}
        for reference in references:
            if reference.get("is_debug"):
                # Skip debug exercises when building prompts, but leave the flag in state.
                continue
            checker_prompt = _build_checker_prompt(subtopic, reference)
            prompts[subtopic_id][reference["solution_id"]] = SubtopicPrompt(
                subtopic_id=subtopic_id,
                topic_name=subtopic["topic_name"],
                rubric_text=subtopic["text"],
                reference_solution_id=reference["solution_id"],
                reference_filename=reference["filename"],
                checker_prompt=checker_prompt,
            )
            prompts_by_exercise.setdefault(reference["solution_id"], {})[
                subtopic_id
            ] = prompts[subtopic_id][reference["solution_id"]]

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

def _strip_quotes(value: str) -> str:
    if (
        len(value) >= 2
        and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'"))
    ):
        return value[1:-1]
    return value


def _fallback_parse_rubric(rubric_text: str) -> Dict:
    """Parse the rubric when PyYAML is unavailable."""
    topics: List[Dict] = []
    current_topic: Optional[Dict] = None
    current_subtopic: Optional[Dict] = None

    def flush_subtopic() -> None:
        nonlocal current_subtopic, current_topic
        if current_topic is not None and current_subtopic is not None:
            current_topic.setdefault("subtopics", []).append(current_subtopic)
            current_subtopic = None

    def flush_topic() -> None:
        nonlocal current_topic
        if current_topic is not None:
            flush_subtopic()
            topics.append(current_topic)
            current_topic = None

    in_topics_section = False
    for raw_line in rubric_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("topics:"):
            in_topics_section = True
            continue
        if not in_topics_section:
            continue

        indent = len(line) - len(stripped)

        if indent == 2 and stripped.startswith("- id:"):
            flush_topic()
            topic_id = _strip_quotes(stripped.split(":", 1)[1].strip())
            current_topic = {"id": topic_id, "name": "", "subtopics": []}
        elif indent == 4 and stripped.startswith("name:") and current_topic:
            current_topic["name"] = _strip_quotes(stripped.split(":", 1)[1].strip())
        elif indent == 4 and stripped.startswith("subtopics:"):
            flush_subtopic()
        elif indent == 6 and stripped.startswith("- id:") and current_topic:
            flush_subtopic()
            subtopic_id = _strip_quotes(stripped.split(":", 1)[1].strip())
            current_subtopic = {"id": subtopic_id, "text": ""}
        elif indent == 8 and stripped.startswith("text:") and current_subtopic:
            current_subtopic["text"] = _strip_quotes(stripped.split(":", 1)[1].strip())

    flush_topic()
    return {"topics": topics}
