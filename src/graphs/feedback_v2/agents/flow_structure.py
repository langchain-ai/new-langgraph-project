from .base import BaseAgent

class FlowStructureAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "Flow & Structure Agent"

    @property
    def role_description(self) -> str:
        return "Analyze the execution flow and logical structure of the solution."

    def get_system_prompt(self) -> str:
        return """
Analyze the student's code for:
1. **Logical Flow**: Does the program flow logically from start to finish? Are there infinite loops or unreachable code?
2. **Requirement Coverage**: Does the structure align with the exercise requirements?
3. **Correctness of Logic**: Are the algorithms implemented correctly for the given problem?

Ignore syntax errors or style issues unless they break the logic.
"""
