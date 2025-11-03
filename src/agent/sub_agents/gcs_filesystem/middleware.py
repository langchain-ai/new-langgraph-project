"""Middleware for GCS filesystem sub-agent."""

from langchain.agents.middleware.types import AgentMiddleware

from src.agent.tools.shared.gcs.validation import set_gcs_root_path


class GCSRuntimeMiddleware(AgentMiddleware):
    """
    Middleware that extracts gcs_root_path from state for GCS tools.

    NOTE: Reads from state instead of config due to deepagents SubAgentMiddleware
    not propagating RunnableConfig to sub-agents. The main agent's ConfigToStateMiddleware
    copies gcs_root_path from config.configurable to state.
    """

    def __init__(self):
        self.state_key = "gcs_root_path"

    def before_agent(self, state, runtime):
        """Extract and validate gcs_root_path from state."""
        # Read from state (propagated by ConfigToStateMiddleware in main agent)
        root_path = state.get(self.state_key)

        if not root_path:
            raise ValueError(
                f"Missing required state key: '{self.state_key}'. "
                f"Ensure ConfigToStateMiddleware is configured in main agent. "
                f"Expected format: /company-{{id}}/workspace-{{id}}/"
            )

        # Normalize path format
        if not root_path.startswith("/"):
            root_path = f"/{root_path}"
        if not root_path.endswith("/"):
            root_path = f"{root_path}/"

        # Set root_path in context for tools to use
        # This validates the format using the proper regex pattern
        set_gcs_root_path(root_path)

        return None