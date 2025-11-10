"""State schema for the main agent with GCS runtime configuration."""

from typing import Any, Dict

from langchain.agents.middleware.types import AgentState


class MainAgentState(AgentState):
    """Extended state schema with GCS runtime configuration.

    Extends AgentState to include gcs_root_path which is required for
    multi-tenant filesystem isolation. This path is provided per-request
    by the frontend via config.configurable.

    Also includes mention_context for @[filename] mention system, where
    the frontend pre-loads file/folder content and sends it with the request.

    Attributes:
        gcs_root_path: Runtime GCS path for workspace isolation.
                      Format: /company-{id}/workspace-{id}/
        mention_context: Pre-loaded content from @mentions (dict format).
                        Validated by ConfigToStateMiddleware using MentionContext schema.
                        Stored as dict for LangGraph serialization compatibility.
    """

    gcs_root_path: str | None
    mention_context: Dict[str, Any] | None
