from .base import BaseAgent

class FunctionDivisionAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "Function Division Agent"

    @property
    def role_description(self) -> str:
        return "Evaluate the modularity and function breakdown of the code."

    def get_system_prompt(self) -> str:
        return """
Analyze the student's code for:
1. **Modularity**: Is the code properly divided into functions? 
2. **Single Responsibility**: Does each function do one thing?
3. **Redundancy**: Is there duplicated code that should be extracted to a function?
4. **Main Function**: Is there a main execution block/function?

Focus ONLY on how the code is organized into functions.
"""
