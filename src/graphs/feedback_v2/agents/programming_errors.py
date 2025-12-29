from .base import BaseAgent

class ProgrammingErrorsAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "Programming Errors Agent"

    @property
    def role_description(self) -> str:
        return "Detect bugs, syntax errors, and potential runtime issues."

    def get_system_prompt(self) -> str:
        return """
Analyze the student's code for:
1. **Syntax Errors**: Invalid Python syntax.
2. **Runtime Errors**: Potential crashes (e.g., division by zero, index out of bounds, type mismatches).
3. **Logic Bugs**: Implementation flaws that lead to incorrect results (e.g., off-by-one errors).
4. **Input Handling**: improper handling of user input.

Focus ONLY on bugs and errors. Do not comment on style or modularity.
"""
