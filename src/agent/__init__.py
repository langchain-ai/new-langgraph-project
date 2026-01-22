"""5STARS LangGraph Agent.

Multi-agent system for automated Wildberries review management.

Main components:
- graph: The compiled LangGraph workflow
- process_case: Process a new review case
- process_message: Handle customer message in existing case
- CaseState: Central state TypedDict
- CaseStage: Case processing stages enum
"""

from agent.graph import graph, process_case, process_message
from agent.state import AgentContext, CaseStage, CaseState

__all__ = [
    "graph",
    "process_case",
    "process_message",
    "CaseState",
    "CaseStage",
    "AgentContext",
]
