"""Utility functions shared by GCS filesystem tools."""

from src.agent.tools.shared.gcs.validation import get_gcs_root_path
from src.agent.tools.shared.gcs.client import get_gcs_client


def ensure_runtime_root_path():
    """Ensure runtime root path is set and return it."""
    return get_gcs_root_path()


def setup_gcs_bucket(bucket_name):
    """Setup GCS bucket with runtime validation.

    Ensures runtime root path is configured and returns bucket instance.
    """
    ensure_runtime_root_path()
    client = get_gcs_client()
    return client.bucket(bucket_name)


def normalize_gcs_blob_path(path):
    """Normalize file path to GCS blob path by removing leading slash."""
    return path.lstrip("/")