"""LangGraph single-node graph template.

Returns a predefined response. Replace logic and configuration as needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph


class Configuration(TypedDict):
    """Configurable parameters for the agent.

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
    changeme: str = "example"


async def my_node(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Example node: processes input and returns output.

    Can use runtime configuration to alter behavior.
    """
    configuration = config["configurable"]
    return {
        "changeme": "output from my_node. "
        f'Configured with {configuration.get("my_configurable_param")}'
    }


# Define the graph
graph = (
    StateGraph(State, config_schema=Configuration)
    .add_node(my_node)
    .add_edge("__start__", "my_node")
    .compile(name="New Graph")
)
