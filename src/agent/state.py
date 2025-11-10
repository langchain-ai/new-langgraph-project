"""State schema for the main agent with GCS runtime configuration."""

from langchain.agents.middleware.types import AgentState

from src.agent.schemas.mention_context import MentionContext


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
        mention_context: Validated pre-loaded content from @mentions.
                        See MentionContext schema for structure.
    """

    gcs_root_path: str | None
    mention_context: MentionContext | None
