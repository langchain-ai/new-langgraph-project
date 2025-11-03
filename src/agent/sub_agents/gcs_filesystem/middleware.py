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
        """Extract and validate gcs_root_path from state."""
        root_path = state.get(self.state_key)

        if not root_path:
            raise ValueError(
                f"Missing '{self.state_key}' in state. "
                f"Ensure ConfigToStateMiddleware is configured. "
                f"Expected format: /company-{{id}}/workspace-{{id}}/"
            )

        # Normalize path format
        normalized = root_path
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        if not normalized.endswith("/"):
            normalized = f"{normalized}/"

        # Validate format
        validate_root_path(normalized)

        # Update state with normalized path if changed
        if normalized != root_path:
            logger.info(f"[GCSRuntime] Normalized path: {root_path} -> {normalized}")
            return {self.state_key: normalized}

        return None

    async def abefore_agent(self, state, runtime):
        """Extract and validate gcs_root_path from state (async)."""
        return self.before_agent(state, runtime)