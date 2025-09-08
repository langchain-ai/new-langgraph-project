"""LangGraph hello agent.

Returns a friendly greeting message.
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

    greeting_style: str


@dataclass
class State:
    """Input state for the agent.

    Defines the initial structure of incoming data.
    See: https://langchain-ai.github.io/langgraph/concepts/low_level/#state
    """

    name: str = ""


async def greet(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Returns a friendly greeting message."""
    name = state.name or "World"
    
    # Check for greeting style configuration
    style = "casual"
    if runtime.context:
        style = runtime.context.get('greeting_style', 'casual')
    
    if style == "formal":
        greeting = f"Good day, {name}!"
    elif style == "enthusiastic":
        greeting = f"Hello there, {name}! 🎉"
    else:  # casual
        greeting = f"Hello, {name}!"
    
    return {"message": greeting}


# Define the graph
graph = (
    StateGraph(State, context_schema=Context)
    .add_node(greet)
    .add_edge("__start__", "greet")
    .compile(name="Hello Agent")
)