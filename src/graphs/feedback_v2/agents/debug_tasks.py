from .base import BaseAgent

class DebugTasksAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "Debug Tasks Agent"

    @property
    def role_description(self) -> str:
        return "Verify that specific debugging tasks were completed correctly."

    def get_system_prompt(self) -> str:
        return """
This agent is relevant ONLY if the exercise involves fixing a specific bug or refactoring bad code.

Analyze the student's code for:
1. **Bug Fixes**: Did the student fix the issues mentioned in the exercise description?
2. **Regression**: Did the fix introduce new bugs?
3. **Partial Fixes**: Did they only fix part of the problem?

If this is NOT a debug/refactor exercise, simply PASS with no comments.
"""
