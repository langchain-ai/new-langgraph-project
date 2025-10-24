
from src.core.shared_state import SharedState

class UnitTester:
    """
    The UnitTester agent runs the student program(s) with sample inputs
    and validates the outputs against expected results defined in the rubric.
    """

    def run(self, state: SharedState) -> SharedState:
        """
        Runs unit tests on the compiled student program.

        Args:
            state: The current shared state.

        Returns:
            The updated shared state with unit test findings.
        """
        print("UnitTester: Running tests...")
        submission_path = state.get("submission_path")
        rubric = state.get("rubric", {})
        test_cases = rubric.get("unit_tests", [])

        test_results = []

        # Placeholder: The path to the compiled executable from the CompilerRunner agent.
        executable_path = f"{submission_path}/program"

        # for test_case in test_cases:
        #     sample_input = test_case.get("input")
        #     expected_output = test_case.get("output")
        #
        #     # Placeholder: Run the student's program with the sample input.
        #     # from src.tools.shell_tool import run_shell_command
        #     # actual_output = run_shell_command(f"echo '{sample_input}' | {executable_path}")
        #     actual_output = "some output" # Example
        #
        #     # Placeholder: Compare the actual output with the expected output.
        #     if actual_output.strip() == expected_output.strip():
        #         test_results.append({"test": sample_input, "result": "Pass"})
        #     else:
        #         test_results.append({"test": sample_input, "result": "Fail"})

        test_summary = "Placeholder: 2/3 tests passed." # Example summary

        # Placeholder: Update the `findings` dictionary in the shared state.
        if "findings" not in state:
            state["findings"] = {}
        state["findings"]["unit_tests"] = test_summary
        
        print(f"UnitTester: Testing complete. {test_summary}")
        
        return state
