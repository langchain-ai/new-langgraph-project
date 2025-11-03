"""State schema for the main agent with GCS runtime configuration."""

from typing import Optional

from langchain.agents.middleware.types import AgentState


class MainAgentState(AgentState):
    """Extended state schema with GCS runtime configuration.

    Extends AgentState to include gcs_root_path which is required for
    multi-tenant filesystem isolation. This path is provided per-request
    by the frontend via config.configurable.

    Attributes:
        gcs_root_path: Runtime GCS path for workspace isolation.
                      Format: /company-{id}/workspace-{id}/
    """

    gcs_root_path: Optional[str]
