"""Define a simple chatbot agent.

This agent returns a predefined response without using an actual LLM.
"""

from typing import Any, Dict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph

from agent.configuration import Configuration
from agent.state import State


async def my_node(state: State, config: RunnableConfig) -> Dict[str, Any]:
    """Each node does work."""
    configuration = Configuration.from_runnable_config(config)
    # configuration = Configuration.from_runnable_config(config)
    # You can use runtime configuration to alter the behavior of your
    # graph.
    return {
        "changeme": "output from my_node. "
        f"Configured with {configuration.my_configurable_param}"
    }


# Define a new graph
workflow = StateGraph(State, config_schema=Configuration)

# Add the node to the graph
workflow.add_node("my_node", my_node)

# Set the entrypoint as `call_model`
workflow.add_edge("__start__", "my_node")

# Compile the workflow into an executable graph
graph = workflow.compile()
graph.name = "New Graph"  # This defines the custom name in LangSmith
