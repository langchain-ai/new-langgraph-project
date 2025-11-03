"""
Middleware to propagate runtime config to state for sub-agent access.

WORKAROUND: deepagents SubAgentMiddleware doesn't propagate RunnableConfig
to sub-agents when calling subagent.ainvoke(state). This middleware copies
config values to state so they can be accessed by sub-agents.

This is a self-contained workaround that can be removed when deepagents
fixes config propagation (see: https://github.com/anthropics/deepagents/issues/XXX)
"""

from langgraph.config import get_config
from langchain.agents.middleware.types import AgentMiddleware


class ConfigToStateMiddleware(AgentMiddleware):
    """
    Copy gcs_root_path from config.configurable to state.

    This enables sub-agents to access runtime configuration that would
    otherwise be lost due to SubAgentMiddleware not propagating config.
    """

    def before_agent(self, state, runtime):
        """Extract gcs_root_path from config and add to state."""
        config = get_config()
        configurable = config.get("configurable", {})
        gcs_root_path = configurable.get("gcs_root_path")

        if gcs_root_path:
            state["gcs_root_path"] = gcs_root_path

        return None
