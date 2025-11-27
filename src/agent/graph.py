"""LangGraph single-node graph template.

Uses Anthropic Claude to respond to messages.
"""

from __future__ import annotations

from typing import Annotated

from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.runtime import Runtime
from typing_extensions import TypedDict


class Context(TypedDict):
    """Context parameters for the agent.

    Set these when creating assistants OR when invoking the graph.
    See: https://langchain-ai.github.io/langgraph/cloud/how-tos/configuration_cloud/
    """

    model: str


class State(TypedDict):
    """Input state for the agent.

    Uses the standard messages pattern for chat applications.
    See: https://langchain-ai.github.io/langgraph/concepts/low_level/#state
    """

    messages: Annotated[list, add_messages]


async def call_model(state: State, runtime: Runtime[Context]) -> dict:
    """Process input messages using Claude and returns the response.

    Can use runtime context to configure the model.
    """
    # Get model name from context or use default
    model_name = (runtime.context or {}).get("model", "claude-3-5-sonnet-20241022")

    # Initialize the LLM
    llm = ChatAnthropic(model=model_name)

    # Invoke the model with the messages
    response = await llm.ainvoke(state["messages"])

    return {"messages": [response]}


# Define the graph
graph = (
    StateGraph(State, context_schema=Context)
    .add_node(call_model)
    .add_edge("__start__", "call_model")
    .compile(name="New Graph")
)
