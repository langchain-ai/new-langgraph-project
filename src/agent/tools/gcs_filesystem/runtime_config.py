"""Runtime configuration management for GCS tools.

This module handles the runtime configuration passed from the frontend,
specifically the gcs_root_path that comes with each request.
"""

import contextvars
from typing import Optional
from src.agent.tools.shared.gcs.validation import set_gcs_root_path as validate_and_set_root_path

# Context variable to store the current root path for the request
_current_root_path: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "gcs_root_path", default=None
)


def set_runtime_root_path(root_path: str) -> None:
    """Set the root path for the current request context.

    This is typically called by middleware when processing a request
    with the gcs_root_path from the frontend config.

    Args:
        root_path: The GCS root path for the current request
    """
    # Validate format before setting in both contexts
    validate_and_set_root_path(root_path)  # This validates with regex
    _current_root_path.set(root_path)  # Also set in our context var


def get_runtime_root_path() -> Optional[str]:
    """Get the root path for the current request context.

    Returns:
        The current GCS root path, or None if not set
    """
    return _current_root_path.get()


def clear_runtime_root_path() -> None:
    """Clear the root path from the current context."""
    _current_root_path.set(None)


# RuntimeConfigMiddleware has been moved to middleware.py
# This file only contains context variable management functions