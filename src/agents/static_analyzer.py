
from src.core.shared_state import SharedState

class StaticAnalyzer:
    """
    The StaticAnalyzer agent checks the student's code for style and conventions.
    (e.g., naming conventions, brace style, initialization, declarations at the top, etc.)
    """

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

        # Placeholder: Use a command-line tool (like cppcheck, clang-tidy, or a custom script)
        # to analyze the code at `submission_path`.
        # from src.tools.shell_tool import run_shell_command
        # analysis_results = run_shell_command(f"your-linter --path {submission_path}")
        
        analysis_results = "Placeholder: 2 style issues found." # Example result

        # Placeholder: Parse the results from the tool.
        
        # Placeholder: Update the `findings` dictionary in the shared state.
        if "findings" not in state:
            state["findings"] = {}
        state["findings"]["static_analysis"] = analysis_results
        
        print(f"StaticAnalyzer: Analysis complete. {analysis_results}")
        
        return state
