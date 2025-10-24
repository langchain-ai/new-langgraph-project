from typing import TypedDict, List, Dict

class Grade(TypedDict):
    """Represents a single graded item from the rubric."""
    name: str
    points_earned: int
    points_possible: int
    comment: str

class GradingResult(TypedDict):
    """Represents the overall grading result for a submission."""
    student_id: str
    total_points_earned: int
    total_points_possible: int
    grades: List[Grade]
    general_feedback: str

class SharedState(TypedDict):
    """
    Manages the shared state that is passed between agents in the graph.
    """
    submission_path: str
    rubric_path: str
    rubric: Dict
    findings: Dict
    grading_result: GradingResult
