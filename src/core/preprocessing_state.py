"""TypedDict definitions for the preprocessing graph."""

from __future__ import annotations

from typing import Dict, List, Optional, TypedDict


class ReferenceSolutionInput(TypedDict, total=False):
    """Reference solution descriptor before normalization."""

    solution_id: str
    path: Optional[str]
    code: Optional[str]
    filename: Optional[str]
    is_debug: bool


class ReferenceSolution(TypedDict):
    """Normalized reference solution text."""

    solution_id: str
    code: str
    filename: str
    source_path: Optional[str]
    is_debug: bool


class RubricSubtopic(TypedDict):
    """Flattened rubric subtopic used for prompt generation."""

    subtopic_id: str
    topic_id: str
    topic_name: str
    text: str


class SubtopicPrompt(TypedDict):
    """Prompt entry stored in the final lookup table."""

    subtopic_id: str
    topic_name: str
    rubric_text: str
    reference_solution_id: str
    reference_filename: str
    checker_prompt: str


class ExerciseSubtopic(TypedDict):
    """Per-exercise subtopic definition."""

    id: str
    topic: str
    text: str


class ExerciseRubric(TypedDict, total=False):
    """Exercise-level rubric data (regular or debug)."""

    exercise_id: str
    type: str  # "regular" or "debug"
    subtopics: List[RubricSubtopic]
    fixes: List[str]


class PreprocessingState(TypedDict, total=False):
    """State object that flows through the preprocessing graph."""

    rubric_path: str
    metadata: Dict[str, str]
    reference_solutions: List[ReferenceSolutionInput]
    debug_exercises: List[str]
    rubric: Dict
    exercise_rubrics: Dict[str, ExerciseRubric]
    normalized_reference_solutions: List[ReferenceSolution]
    prompts_by_subtopic: Dict[str, Dict[str, SubtopicPrompt]]
    prompts_by_exercise: Dict[str, Dict[str, SubtopicPrompt]]
