"""Utility functions shared by GCS filesystem tools."""

from langchain.tools import ToolRuntime

from src.agent.tools.shared.gcs.client import get_gcs_client


def get_root_path_from_runtime(runtime: ToolRuntime) -> str:
    """Extract gcs_root_path from tool runtime state.

    Args:
        runtime: Tool runtime with state

    Returns:
        GCS root path from state

    Raises:
        RuntimeError: If runtime or gcs_root_path not available
    """
    if not runtime or "gcs_root_path" not in runtime.state:
        raise RuntimeError(
            "GCS root path not found in runtime state. "
            "Ensure GCSRuntimeMiddleware is configured."
        )
    return runtime.state["gcs_root_path"]


def setup_gcs_bucket(bucket_name):
    """Setup GCS bucket instance.

    Args:
        bucket_name: Name of the GCS bucket

    Returns:
        GCS bucket instance
    """
    client = get_gcs_client()
    return client.bucket(bucket_name)


def normalize_gcs_blob_path(path):
    """Normalize file path to GCS blob path by removing leading slash."""
    return path.lstrip("/")