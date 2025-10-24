
from src.core.shared_state import SharedState
import os
import openai
from dotenv import load_dotenv

load_dotenv()

class StaticAnalyzer:
    """
    The StaticAnalyzer agent checks the student's code for style and conventions.
    (e.g., naming conventions, brace style, initialization, declarations at the top, etc.)
    """

    def __init__(self):
        """Initializes the StaticAnalyzer agent, setting up the OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        self.client = openai.OpenAI(api_key=api_key)

    def run(self, state: SharedState) -> SharedState:
        """
        Runs static analysis on the student's code.

        Args:
            state: The current shared state, containing the path to the submission.

        Returns:
            The updated shared state with static analysis findings.
        """
        print("StaticAnalyzer: Running analysis...")
        submission_path = state.get("submission_path")

        # Placeholder: Instead of a linter, use the OpenAI client to analyze the code.
        # You would first read the code from the submission_path.
        # with open(f"{submission_path}/main.c", "r") as f:
        #     code = f.read()
        #
        # analysis_prompt = f"Please analyze this C code for style and conventions. Check for naming, brace style, and declarations. Provide feedback. Code: \n\n{code}"
        # response = self.client.chat.completions.create(
        #     model="gpt-4",
        #     messages=[
        #         {"role": "system", "content": "You are a C programming style checker."},
        #         {"role": "user", "content": analysis_prompt}
        #     ]
        # )
        # analysis_results = response.choices[0].message.content
        
        analysis_results = "Placeholder: 2 style issues found by AI." # Example result

        # Placeholder: Update the `findings` dictionary in the shared state.
        if "findings" not in state:
            state["findings"] = {}
        state["findings"]["static_analysis"] = analysis_results
        
        print(f"StaticAnalyzer: Analysis complete. {analysis_results}")
        
        return state
