"""Middleware to build GCS path from config and propagate to state.

WORKAROUND: deepagents SubAgentMiddleware doesn't propagate RunnableConfig
to sub-agents. This middleware builds the GCS path from company_slug and
workspace_slug, then copies it to state for sub-agent access.
"""

import logging

from langchain.agents.middleware.types import AgentMiddleware
from langgraph.config import get_config

logger = logging.getLogger(__name__)

GCS_ROOT_PREFIX = "athena-enterprise"


class ConfigToStateMiddleware(AgentMiddleware):
    """Build GCS path from company_slug and workspace_slug, propagate to state.

    Constructs real GCS path: athena-enterprise/{company_slug}/{workspace_slug}/
    This enables sub-agents to access runtime configuration.

    REQUIRED: company_slug and workspace_slug in config.configurable.
    """

    def _build_gcs_path(self):
        """Build GCS path from company_slug and workspace_slug.

        Returns:
            dict: State update with gcs_root_path

        Raises:
            ValueError: If required config missing
        """
        config = get_config()
        configurable = config.get("configurable", {})

        company_slug = configurable.get("company_slug")
        workspace_slug = configurable.get("workspace_slug")

        if not company_slug or not workspace_slug:
            raise ValueError(
                "Missing required config: 'company_slug' and 'workspace_slug'. "
                "Frontend must provide both in config.configurable."
            )

        # Build real GCS path: athena-enterprise/{company_slug}/{workspace_slug}/
        gcs_root_path = f"{GCS_ROOT_PREFIX}/{company_slug}/{workspace_slug}/"

        logger.info(
            f"[ConfigToState] Built GCS path: {gcs_root_path} "
            f"(company={company_slug}, workspace={workspace_slug})"
        )

        return {"gcs_root_path": gcs_root_path}

    def before_agent(self, state, runtime):
        """Build GCS path and propagate to state (sync)."""
        return self._build_gcs_path()

    async def abefore_agent(self, state, runtime):
        """Build GCS path and propagate to state (async)."""
        return self._build_gcs_path()
