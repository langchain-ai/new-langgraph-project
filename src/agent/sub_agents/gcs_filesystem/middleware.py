"""Middleware for GCS filesystem sub-agent.

This middleware handles the runtime configuration passed from the frontend,
specifically extracting the gcs_root_path from the config.
"""

from typing import Any, Optional

from src.agent.tools.gcs_filesystem.runtime_config import set_runtime_root_path, clear_runtime_root_path


from langchain.agents.middleware.types import AgentMiddleware


class GCSRuntimeMiddleware(AgentMiddleware):
    """Middleware that extracts gcs_root_path from config for GCS tools.

    This middleware intercepts the runtime config passed from the frontend
    and makes the gcs_root_path available to GCS tools via context variables.
    """

    def __init__(self):
        self.config_key = "gcs_root_path"

    def before_agent(self, state: Any, runtime: Any) -> Optional[dict]:
        """Extract and validate gcs_root_path from runtime config.

        Args:
            state: Agent state
            runtime: Runtime configuration containing frontend config

        Returns:
            None

        Raises:
            ValueError: If gcs_root_path is missing or invalid
        """
        # Extract configurable from runtime
        configurable = runtime.config.get("configurable", {})
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
        # This also validates the format using the proper regex pattern
        set_runtime_root_path(root_path)

        return None