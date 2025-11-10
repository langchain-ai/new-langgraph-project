"""Middleware to build GCS path from config and propagate to state.

WORKAROUND: deepagents SubAgentMiddleware doesn't propagate RunnableConfig
to sub-agents. This middleware builds the GCS path from company_slug and
workspace_slug, then copies it to state for sub-agent access.

Also extracts mention_context from config if present (used by @mention system).
"""

import logging
import re

from langchain.agents.middleware.types import AgentMiddleware
from langgraph.config import get_config
from pydantic import ValidationError

from src.agent.schemas.mention_context import MentionContext

logger = logging.getLogger(__name__)

# Slug validation pattern: alphanumeric, hyphens, underscores, 1-63 chars
SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-_]{0,61}[a-zA-Z0-9])?$")


class ConfigToStateMiddleware(AgentMiddleware):
    """Build GCS path from company_slug and workspace_slug, propagate to state.

    Constructs GCS path inside bucket: {company_slug}/{workspace_slug}/
    (bucket name is separate in tools configuration)

    Also extracts mention_context if present (used by @mention system).

    REQUIRED: company_slug and workspace_slug in config.configurable.
    OPTIONAL: mention_context in config.configurable.
    """

    def _validate_slug(self, slug: str, slug_type: str) -> None:
        """Validate slug format for security.

        Args:
            slug: Slug to validate
            slug_type: Type of slug (for error messages)

        Raises:
            ValueError: If slug format is invalid
        """
        if not slug or not isinstance(slug, str):
            raise ValueError(f"Invalid {slug_type}: must be non-empty string")

        if not SLUG_PATTERN.match(slug):
            raise ValueError(
                f"Invalid {slug_type}: '{slug}'. "
                f"Must be alphanumeric with hyphens/underscores, 1-63 chars"
            )

    def _validate_mention_paths(
        self, mention_context: MentionContext, gcs_root_path: str
    ) -> None:
        """Validate all paths in mention_context are within workspace.

        Args:
            mention_context: Validated mention context structure
            gcs_root_path: Workspace root path

        Raises:
            ValueError: If any path is invalid or escapes workspace
        """
        from src.agent.tools.shared.gcs.validation import validate_path

        # Validate file paths
        for file_info in mention_context.files:
            try:
                validate_path(file_info.path, gcs_root_path)
            except ValueError as e:
                logger.error(f"[ConfigToState] Invalid file path: {file_info.path}")
                raise ValueError(f"Invalid file path in mentions: {file_info.path}") from e

        # Validate folder paths
        for folder_info in mention_context.folders:
            try:
                validate_path(folder_info.path, gcs_root_path)
            except ValueError as e:
                logger.error(f"[ConfigToState] Invalid folder path: {folder_info.path}")
                raise ValueError(f"Invalid folder path in mentions: {folder_info.path}") from e

    def _build_state_from_config(self):
        """Build state from config (GCS path + mention context).

        Returns:
            dict: State update with gcs_root_path and mention_context

        Raises:
            ValueError: If required config missing or invalid
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

        # Validate slug formats for security
        self._validate_slug(company_slug, "company_slug")
        self._validate_slug(workspace_slug, "workspace_slug")

        # Build GCS path inside bucket: {company_slug}/{workspace_slug}/
        gcs_root_path = f"{company_slug}/{workspace_slug}/"

        state_update = {"gcs_root_path": gcs_root_path}

        # Extract and validate mention context (optional)
        mention_context_raw = configurable.get("mention_context")
        if mention_context_raw:
            try:
                # Validate structure with Pydantic (type safety + size limits)
                mention_context = MentionContext(**mention_context_raw)

                # Validate paths are within workspace (security)
                self._validate_mention_paths(mention_context, gcs_root_path)

                # Store validated mention context
                state_update["mention_context"] = mention_context

                logger.info(
                    f"[ConfigToState] Validated mention_context with "
                    f"{len(mention_context.files)} files, "
                    f"{len(mention_context.folders)} folders"
                )

            except ValidationError as e:
                logger.error(f"[ConfigToState] Invalid mention_context structure: {e}")
                raise ValueError(f"Invalid mention_context format: {e}") from e
            except ValueError as e:
                # Path validation failed
                logger.error(f"[ConfigToState] mention_context path validation failed: {e}")
                raise

        logger.debug("[ConfigToState] Built GCS path for workspace")

        return state_update

    def before_agent(self, state, runtime):
        """Build state from config and propagate (sync)."""
        return self._build_state_from_config()

    async def abefore_agent(self, state, runtime):
        """Build state from config and propagate (async)."""
        return self._build_state_from_config()
