"""GCS Filesystem Sub-Agent Configuration."""

import os
from typing import Optional

from src.agent.tools.gcs_filesystem import get_gcs_tools
from .prompts import GCS_FILESYSTEM_SYSTEM_PROMPT
from .middleware import GCSRuntimeMiddleware


def create_gcs_filesystem_subagent(
    bucket_name: Optional[str] = None,
    custom_tool_descriptions: Optional[dict] = None,
    model: Optional[str] = None
) -> dict:
    """Create GCS filesystem sub-agent configuration.

    Args:
        bucket_name: GCS bucket name (defaults to GCS_BUCKET_NAME env var)
        custom_tool_descriptions: Optional custom tool descriptions
        model: Optional model override (uses parent model if None)

    Returns:
        Sub-agent configuration dictionary

    Note:
        The gcs_root_path is passed from the frontend in the runtime config.configurable
        and is accessed by the tools at runtime via context variables.
    """
    # Get bucket name from env if not provided
    bucket_name = bucket_name or os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        raise ValueError(
            "GCS bucket name not provided. Set GCS_BUCKET_NAME env var or pass bucket_name parameter."
        )

    # Generate tools for this sub-agent
    # Tools will read root_path from runtime context when executed
    tools = get_gcs_tools(bucket_name, custom_tool_descriptions)

    config = {
        "name": "gcs-filesystem",
        "description": (
            "Specialized agent for GCS file operations. "
            "Use for: listing files, reading files, writing new files, editing existing files. "
            "Handles all Google Cloud Storage filesystem interactions."
        ),
        "system_prompt": GCS_FILESYSTEM_SYSTEM_PROMPT,
        "tools": tools,
        "middleware": [GCSRuntimeMiddleware()],  # Middleware to extract runtime config
    }

    # Only include model if explicitly provided (None means use parent model)
    if model is not None:
        config["model"] = model

    return config


def get_default_gcs_filesystem_subagent() -> dict:
    """Get default GCS filesystem sub-agent configuration.

    This is a lazy factory that creates the sub-agent only when needed.
    The gcs_root_path will be provided at runtime from the frontend config.
    """
    return create_gcs_filesystem_subagent()


# For backward compatibility, we'll create a placeholder that gets populated lazily
_GCS_FILESYSTEM_SUBAGENT = None

def GCS_FILESYSTEM_SUBAGENT():
    """Lazy getter for default GCS filesystem sub-agent."""
    global _GCS_FILESYSTEM_SUBAGENT
    if _GCS_FILESYSTEM_SUBAGENT is None:
        _GCS_FILESYSTEM_SUBAGENT = get_default_gcs_filesystem_subagent()
    return _GCS_FILESYSTEM_SUBAGENT