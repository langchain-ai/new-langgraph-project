"""Middleware to propagate runtime config to state for sub-agent access.

WORKAROUND: deepagents SubAgentMiddleware doesn't propagate RunnableConfig
to sub-agents when calling subagent.ainvoke(state). This middleware copies
config values to state so they can be accessed by sub-agents.

This is a self-contained workaround that can be removed when deepagents
fixes config propagation (see: https://github.com/anthropics/deepagents/issues/XXX)
"""

import logging

from langchain.agents.middleware.types import AgentMiddleware
from langgraph.config import get_config

logger = logging.getLogger(__name__)


class ConfigToStateMiddleware(AgentMiddleware):
    """Copy gcs_root_path from config.configurable to state.

    This enables sub-agents to access runtime configuration that would
    otherwise be lost due to SubAgentMiddleware not propagating config.

    REQUIRED: gcs_root_path must be provided in config.configurable.
    Agent execution will fail if not present.
    """

    def _extract_gcs_root_path(self):
        """Extract and validate gcs_root_path from config.

        Returns:
            dict: State update with gcs_root_path

        Raises:
            ValueError: If gcs_root_path is not provided in config.configurable
        """
        config = get_config()
        logger.info(f"[ConfigToState] Received config keys: {list(config.keys())}")

        configurable = config.get("configurable", {})
        logger.info(f"[ConfigToState] Configurable content: {configurable}")

        gcs_root_path = configurable.get("gcs_root_path")
        logger.info(f"[ConfigToState] Extracted gcs_root_path: {gcs_root_path}")

        if not gcs_root_path:
            error_msg = (
                "Missing required configuration: 'gcs_root_path'. "
                "Frontend must provide gcs_root_path in config.configurable. "
                "Expected format: /company-{id}/workspace-{id}/"
            )
            logger.error(f"[ConfigToState] {error_msg}")
            logger.error(f"[ConfigToState] Full config dump: {config}")
            raise ValueError(error_msg)

        state_update = {"gcs_root_path": gcs_root_path}
        logger.info(f"[ConfigToState] Propagating to state: {state_update}")
        return state_update

    def before_agent(self, state, runtime):
        """Extract gcs_root_path from config and propagate to state (sync).

        Raises:
            ValueError: If gcs_root_path is not provided in config.configurable
        """
        logger.info(f"[ConfigToState] before_agent called with state keys: {list(state.keys())}")
        result = self._extract_gcs_root_path()
        logger.info(f"[ConfigToState] before_agent returning state update: {result}")
        return result

    async def abefore_agent(self, state, runtime):
        """Extract gcs_root_path from config and propagate to state (async).

        Raises:
            ValueError: If gcs_root_path is not provided in config.configurable
        """
        logger.info(f"[ConfigToState] abefore_agent called with state keys: {list(state.keys())}")
        result = self._extract_gcs_root_path()
        logger.info(f"[ConfigToState] abefore_agent returning state update: {result}")
        return result
