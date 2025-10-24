import subprocess
from langsmith import traceable

@traceable
def run_shell_command(command: str) -> str:
    """
    Runs a shell command and returns the output.

    Args:
        command: The command to execute.

    Returns:
        The stdout and stderr of the command.
    """
    try:
        # For security, it's crucial to validate and sanitize the command,
        # especially if it includes any user-provided input.
        # Running in a sandboxed environment (e.g., Docker) is highly recommended.
        print(f"Executing command: {command}")
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            capture_output=True, 
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error executing command:\n{e.stderr}"
