
from src.core.shared_state import SharedState

class CompilerRunner:
    """
    The CompilerRunner agent compiles the student's C code using gcc.
    """

    def run(self, state: SharedState) -> SharedState:
        """
        Compiles the student's C code.

        Args:
            state: The current shared state, containing the path to the submission.

        Returns:
            The updated shared state with compilation findings.
        """
        print("CompilerRunner: Compiling code...")
        submission_path = state.get("submission_path")

        # Placeholder: Find the C source files in the submission directory.
        # This could be done with a glob search.
        source_files = "main.c" # Example file
        output_executable = "program"

        # Placeholder: Construct and run the gcc command.
        # from src.tools.shell_tool import run_shell_command
        # compile_command = f"gcc {submission_path}/{source_files} -o {submission_path}/{output_executable}"
        # compile_result = run_shell_command(compile_command)
        
        compile_result = "Placeholder: Compilation successful." # Example result

        # Placeholder: Check the result for compilation errors.
        
        # Placeholder: Update the `findings` dictionary in the shared state.
        if "findings" not in state:
            state["findings"] = {}
        state["findings"]["compilation"] = compile_result
        
        print(f"CompilerRunner: Compilation complete. {compile_result}")
        
        return state
