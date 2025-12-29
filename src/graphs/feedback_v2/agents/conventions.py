from .base import BaseAgent

class ConventionsAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "Conventions & Documentation Agent"
    
    @property
    def role_description(self) -> str:
        return "Check for adherence to PEP8, naming conventions, and documentation standards."

    def get_system_prompt(self) -> str:
        return """
Analyze the student's code for:
1. **PEP8 Compliance**: Indentation, spacing, line length.
2. **Naming Conventions**: snake_case for functions/vars, CamelCase for classes, etc.
3. **Internal Documentation**: Are there comments explaining complex logic?
4. **Docstrings**: Do functions have docstrings explaining arguments and returns?

Focus ONLY on code style and documentation.
"""
