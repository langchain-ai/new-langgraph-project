"""Centralized model configuration for Claude agents and sub-agents.

Model Identifiers (as of January 2025):
- Haiku 4.5: claude-haiku-4-5-20251001
- Sonnet 4.5: claude-sonnet-4-5-20250929
"""

# Model identifiers
CLAUDE_HAIKU_4_5 = "claude-haiku-4-5-20251001"
CLAUDE_SONNET_4_5 = "claude-sonnet-4-5-20250929"

# Default model for main agent (if not specified)
DEFAULT_MAIN_AGENT_MODEL = CLAUDE_SONNET_4_5

# Sub-agent model mapping
SUBAGENT_MODELS = {
    "gcs-filesystem": CLAUDE_HAIKU_4_5,
}


def get_subagent_model(subagent_name: str) -> str:
    """Get the configured model for a specific sub-agent.

    Args:
        subagent_name: Name of the sub-agent (e.g., 'gcs-filesystem')

    Returns:
        Model identifier string, or None if no specific model configured
        (None means the sub-agent will inherit from parent agent)
    """
    return SUBAGENT_MODELS.get(subagent_name)
