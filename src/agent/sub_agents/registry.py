"""Central registry for all sub-agents."""

from .gcs_filesystem import GCS_FILESYSTEM_SUBAGENT


def get_subagents():
    """Get list of all available sub-agents.

    This is a factory function that creates sub-agents on demand,
    allowing environment variables to be set before creation.
    """
    return [
        GCS_FILESYSTEM_SUBAGENT(),  # Call the lazy getter
        # Future sub-agents will be added here
    ]


# For backward compatibility, create SUBAGENTS dynamically
SUBAGENTS = get_subagents

# Export for easy access
__all__ = ["SUBAGENTS", "get_subagents"]