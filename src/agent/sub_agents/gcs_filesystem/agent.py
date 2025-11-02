"""GCS Filesystem Sub-Agent Configuration."""

import os
from typing import Optional

from src.agent.tools.gcs_filesystem import get_gcs_tools
from .prompts import GCS_FILESYSTEM_SYSTEM_PROMPT


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
    """
    # Get bucket name from env if not provided
    bucket_name = bucket_name or os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        raise ValueError(
            "GCS bucket name not provided. Set GCS_BUCKET_NAME env var or pass bucket_name parameter."
        )

    # Generate tools for this sub-agent
    tools = get_gcs_tools(bucket_name, custom_tool_descriptions)

    return {
        "name": "gcs-filesystem",
        "description": (
            "Specialized agent for GCS file operations. "
            "Use for: listing files, reading files, writing new files, editing existing files. "
            "Handles all Google Cloud Storage filesystem interactions."
        ),
        "system_prompt": GCS_FILESYSTEM_SYSTEM_PROMPT,
        "tools": tools,
        "model": model,  # None means use parent model
    }


# Default sub-agent instance
GCS_FILESYSTEM_SUBAGENT = create_gcs_filesystem_subagent()