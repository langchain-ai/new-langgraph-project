
from src.core.shared_state import SharedState

class RubricScorer:
    """
    The RubricScorer agent maps all the findings from the previous agents
    to the Hebrew rubric, calculating points and generating comments.
    """

    def run(self, state: SharedState) -> SharedState:
        """
        Scores the submission based on the findings and the rubric.

        Args:
            state: The current shared state, containing findings and the rubric.

        Returns:
            The final updated state with the grading result.
        """
        print("RubricScorer: Scoring submission...")
        findings = state.get("findings", {})
        rubric = state.get("rubric", {})
        
        # Placeholder: This is where the core logic of scoring happens.
        # You would iterate through the rubric sections and check the
        # corresponding findings to assign points and comments.
        
        # Example Logic:
        # compilation_points = 0
        # if findings.get("compilation") == "Placeholder: Compilation successful.":
        #     compilation_points = rubric.get("compilation", {}).get("points", 0)

        # The final result should be structured according to the GradingResult TypedDict.
        final_grade = {
            "student_id": "student_123",
            "total_points_earned": 85,
            "total_points_possible": 100,
            "grades": [
                {"name": "Compilation", "points_earned": 20, "points_possible": 20, "comment": "מעולה"},
                {"name": "Style", "points_earned": 15, "points_possible": 20, "comment": "יש לשפר את שמות המשתנים"},
                {"name": "Unit Tests", "points_earned": 50, "points_possible": 60, "comment": "מבחן אחד נכשל"},
            ],
            "general_feedback": "עבודה טובה מאוד, אך יש לשים לב להערות."
        }

        state["grading_result"] = final_grade
        
        print("RubricScorer: Scoring complete.")
        
        return state
