"""Middleware for GCS filesystem sub-agent."""

from langgraph.config import get_config
from langchain.agents.middleware.types import AgentMiddleware

from src.agent.tools.shared.gcs.validation import set_gcs_root_path


class GCSRuntimeMiddleware(AgentMiddleware):
    """Middleware that extracts gcs_root_path from config for GCS tools."""

    def __init__(self):
        self.config_key = "gcs_root_path"

    def before_agent(self, state, runtime):
        """Extract and validate gcs_root_path from runtime config."""
        # Get the RunnableConfig and extract configurable
        config = get_config()
        configurable = config.get("configurable", {})
        root_path = configurable.get(self.config_key)

        if not root_path:
            raise ValueError(
                f"Missing required config: '{self.config_key}'. "
                f"Frontend must provide gcs_root_path in config.configurable. "
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