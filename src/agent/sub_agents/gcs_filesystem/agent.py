"""GCS Filesystem Sub-Agent Configuration."""

import os

from langchain.agents import create_agent

from src.agent.config.models_config import get_subagent_model
from src.agent.state import MainAgentState
from src.agent.tools.gcs_filesystem import get_gcs_tools

from .middleware import GCSRuntimeMiddleware
from .prompts import GCS_FILESYSTEM_SYSTEM_PROMPT


def create_gcs_filesystem_subagent(bucket_name=None, custom_tool_descriptions=None, model=None):
    """Create GCS filesystem sub-agent as CompiledSubAgent with custom state schema.

    Returns a dict with 'name', 'description', and 'runnable' (CompiledSubAgent format).
    The runnable is a compiled graph with MainAgentState schema to receive gcs_root_path.
    """
    # Get bucket name from env if not provided
    bucket_name = bucket_name or os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        raise ValueError(
            "GCS bucket name not provided. Set GCS_BUCKET_NAME env var or pass bucket_name parameter."
        )

    # Get model from config if not provided
    if model is None:
        model = get_subagent_model("gcs-filesystem")
    if model is None:
        raise ValueError("Model must be specified for CompiledSubAgent")

    # Generate tools for this sub-agent
    tools = get_gcs_tools(bucket_name, custom_tool_descriptions)

    # Create compiled graph with custom state schema
    # This ensures gcs_root_path is included in the sub-agent's state
    compiled_subagent = create_agent(
        model=model,
        tools=tools,
        system_prompt=GCS_FILESYSTEM_SYSTEM_PROMPT,
        middleware=[GCSRuntimeMiddleware()],
        state_schema=MainAgentState,  # Include gcs_root_path in state
    )

    # Return CompiledSubAgent format (not SubAgent)
    return {
        "name": "gcs-filesystem",
        "description": (
            "Specialized agent for GCS file operations. "
            "Use for: listing files, reading files, writing new files, editing existing files. "
            "Handles all Google Cloud Storage filesystem interactions."
        ),
        "runnable": compiled_subagent,
    }


def get_default_gcs_filesystem_subagent():
    """Get default GCS filesystem sub-agent configuration."""
    return create_gcs_filesystem_subagent()


# For backward compatibility, we'll create a placeholder that gets populated lazily
_GCS_FILESYSTEM_SUBAGENT = None

def GCS_FILESYSTEM_SUBAGENT():
    """Lazy getter for default GCS filesystem sub-agent."""
    global _GCS_FILESYSTEM_SUBAGENT
    if _GCS_FILESYSTEM_SUBAGENT is None:
        _GCS_FILESYSTEM_SUBAGENT = get_default_gcs_filesystem_subagent()
    return _GCS_FILESYSTEM_SUBAGENT