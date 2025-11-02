"""Central registry for all sub-agents."""

from .gcs_filesystem import GCS_FILESYSTEM_SUBAGENT

# Registry of all available sub-agents
SUBAGENTS = [
    GCS_FILESYSTEM_SUBAGENT,
    # Future sub-agents will be added here
]

# Export for easy access
__all__ = ["SUBAGENTS"]