"""
Middleware to propagate runtime config to state for sub-agent access.

WORKAROUND: deepagents SubAgentMiddleware doesn't propagate RunnableConfig
to sub-agents when calling subagent.ainvoke(state). This middleware copies
config values to state so they can be accessed by sub-agents.

This is a self-contained workaround that can be removed when deepagents
fixes config propagation (see: https://github.com/anthropics/deepagents/issues/XXX)
"""

import logging

from langgraph.config import get_config
from langchain.agents.middleware.types import AgentMiddleware

logger = logging.getLogger(__name__)


class ConfigToStateMiddleware(AgentMiddleware):
    """
    Copy gcs_root_path from config.configurable to state.

    This enables sub-agents to access runtime configuration that would
    otherwise be lost due to SubAgentMiddleware not propagating config.

    REQUIRED: gcs_root_path must be provided in config.configurable.
    Agent execution will fail if not present.
    """

    def _extract_gcs_root_path(self):
        """
        Extract and validate gcs_root_path from config.

        Returns:
            dict: State update with gcs_root_path

        Raises:
            ValueError: If gcs_root_path is not provided in config.configurable
        """
        config = get_config()
        configurable = config.get("configurable", {})
        gcs_root_path = configurable.get("gcs_root_path")

        if not gcs_root_path:
            error_msg = (
                "Missing required configuration: 'gcs_root_path'. "
                "Frontend must provide gcs_root_path in config.configurable. "
                "Expected format: /company-{id}/workspace-{id}/"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.debug(f"Propagating gcs_root_path to state: {gcs_root_path}")
        return {"gcs_root_path": gcs_root_path}

    def before_agent(self, state, runtime):
        """
        Extract gcs_root_path from config and propagate to state (sync).

        Raises:
            ValueError: If gcs_root_path is not provided in config.configurable
        """
        return self._extract_gcs_root_path()

    async def abefore_agent(self, state, runtime):
        """
        Extract gcs_root_path from config and propagate to state (async).

        Raises:
            ValueError: If gcs_root_path is not provided in config.configurable
        """
        return self._extract_gcs_root_path()
