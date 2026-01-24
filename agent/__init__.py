"""5STARS LangGraph Agent.

Single ReAct agent for automated Wildberries review management.

Main components:
- graph: The compiled LangGraph workflow
- CaseState: Central state TypedDict
- AgentConfig: Agent configuration
"""

from agent.graph import graph
from agent.state import AgentConfig, CaseState

__all__ = [
    "graph",
    "CaseState",
    "AgentConfig",
]
