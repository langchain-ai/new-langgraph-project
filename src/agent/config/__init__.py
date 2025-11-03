"""Agent configuration module."""

from .models_config import (
    CLAUDE_HAIKU_4_5,
    CLAUDE_SONNET_4_5,
    DEFAULT_MAIN_AGENT_MODEL,
    SUBAGENT_MODELS,
    get_subagent_model,
)

__all__ = [
    "CLAUDE_HAIKU_4_5",
    "CLAUDE_SONNET_4_5",
    "DEFAULT_MAIN_AGENT_MODEL",
    "SUBAGENT_MODELS",
    "get_subagent_model",
]
