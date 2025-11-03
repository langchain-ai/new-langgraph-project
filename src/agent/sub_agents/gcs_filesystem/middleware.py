"""Middleware for GCS filesystem sub-agent."""

import logging

from langchain.agents.middleware.types import AgentMiddleware

from src.agent.tools.shared.gcs.validation import validate_root_path

logger = logging.getLogger(__name__)


class GCSRuntimeMiddleware(AgentMiddleware):
    """Middleware that validates gcs_root_path from state for GCS tools.

    NOTE: Reads from state instead of config due to deepagents SubAgentMiddleware
    not propagating RunnableConfig to sub-agents. The main agent's ConfigToStateMiddleware
    copies gcs_root_path from config.configurable to state.

    The tools read gcs_root_path directly from runtime.state (not from ContextVar).
    """

    def __init__(self):
        """Initialize GCSRuntimeMiddleware with state key configuration."""
        self.state_key = "gcs_root_path"

    def before_agent(self, state, runtime):
        """Validate gcs_root_path from state."""
        root_path = state.get(self.state_key)

        if not root_path:
            raise ValueError(
                f"Missing '{self.state_key}' in state. "
                f"Ensure ConfigToStateMiddleware is configured."
            )

        # Ensure trailing slash
        if not root_path.endswith("/"):
            normalized = f"{root_path}/"
            logger.info(f"[GCSRuntime] Added trailing slash: {root_path} -> {normalized}")
            validate_root_path(normalized)
            return {self.state_key: normalized}

        # Validate format
        validate_root_path(root_path)
        return None

    async def abefore_agent(self, state, runtime):
        """Extract and validate gcs_root_path from state (async)."""
        return self.before_agent(state, runtime)