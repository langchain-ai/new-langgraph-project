"""LangGraph ping-pong agent.

Returns "pong" regardless of input.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, TypedDict

from langgraph.graph import StateGraph
from langgraph.runtime import Runtime


class Context(TypedDict):
    """Context parameters for the agent.

    Set these when creating assistants OR when invoking the graph.
    See: https://langchain-ai.github.io/langgraph/cloud/how-tos/configuration_cloud/
    """

    my_configurable_param: str


@dataclass
class State:
    """Input state for the agent.

    Defines the initial structure of incoming data.
    See: https://langchain-ai.github.io/langgraph/concepts/low_level/#state
    """

    message: str = ""


async def ping_pong(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Returns 'pong' regardless of input."""
    return {"message": "pong"}


# Define the graph
graph = (
    StateGraph(State, context_schema=Context)
    .add_node(ping_pong)
    .add_edge("__start__", "ping_pong")
    .compile(name="Ping Pong Agent")
)
