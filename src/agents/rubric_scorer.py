
from src.core.shared_state import SharedState
import os
import openai
from dotenv import load_dotenv

load_dotenv()

class RubricScorer:
    """
    The RubricScorer agent maps all the findings from the previous agents
    to the Hebrew rubric, calculating points and generating comments.
    """

    def __init__(self):
        """Initializes the RubricScorer agent, setting up the OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        self.client = openai.OpenAI(api_key=api_key)

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
        
        # Placeholder: Use the OpenAI client to generate Hebrew comments based on findings.
        # For example, for a failed test:
        # feedback_prompt = f"The student's code failed a test. The finding was: {findings.get('unit_tests')}. Please generate a short, encouraging feedback comment in Hebrew."
        # response = self.client.chat.completions.create(
        #     model="gpt-4",
        #     messages=[
        #         {"role": "system", "content": "You are a helpful teaching assistant providing feedback in Hebrew."},
        #         {"role": "user", "content": feedback_prompt}
        #     ]
        # )
        # hebrew_comment = response.choices[0].message.content

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
