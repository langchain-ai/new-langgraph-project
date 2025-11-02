"""Utility functions shared by GCS filesystem tools."""

from .runtime_config import get_runtime_root_path
from src.agent.tools.shared.gcs.validation import set_gcs_root_path


def ensure_runtime_root_path() -> str:
    """Ensure runtime root path is set and return it.

    Returns:
        The validated root path from runtime config

    Raises:
        ValueError: If root path is not found in runtime configuration
    """
    runtime_root_path = get_runtime_root_path()

    if not runtime_root_path:
        raise ValueError(
            "GCS root path not found in runtime configuration. "
            "The frontend must pass 'gcs_root_path' in config.configurable."
        )

    # Set the root path for validation functions
    set_gcs_root_path(runtime_root_path)

    return runtime_root_path