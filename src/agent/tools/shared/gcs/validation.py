import os
import re
from contextvars import ContextVar

_gcs_root_path: ContextVar[str] = ContextVar("gcs_root_path")

COMPANY_WORKSPACE_PATTERN = re.compile(
    r"^/company-[a-zA-Z0-9]([a-zA-Z0-9\-_]{0,61}[a-zA-Z0-9])?/"
    r"workspace-[a-zA-Z0-9]([a-zA-Z0-9\-_]{0,61}[a-zA-Z0-9])?/?$"
)


def _normalize_path(path: str) -> str:
    """
    Normalize path to use forward slashes and ensure leading slash.

    Args:
        path: Path to normalize

    Returns:
        Normalized path with forward slashes and leading slash
    """
    normalized = os.path.normpath(path).replace("\\", "/")
    return f"/{normalized}" if not normalized.startswith("/") else normalized


def get_gcs_root_path() -> str:
    """
    Get current GCS root path from context.

    Raises:
        RuntimeError: If root path not set (middleware not configured)
    """
    try:
        return _gcs_root_path.get()
    except LookupError:
        raise RuntimeError(
            "GCS root path not set. Ensure middleware is properly configured."
        ) from None


def set_gcs_root_path(root_path: str) -> None:
    """
    Set GCS root path in context.

    Args:
        root_path: Must be in format /company-{id}/workspace-{id}/
                  where id contains only alphanumeric, hyphens, and underscores

    Raises:
        ValueError: If root_path format is invalid
    """
    if not COMPANY_WORKSPACE_PATTERN.match(root_path):
        raise ValueError(
            f"Invalid root_path format: '{root_path}'. "
            f"Expected format: /company-{{id}}/workspace-{{id}}/ "
            f"(id: alphanumeric, hyphens, underscores only, 1-63 chars)"
        )
    _gcs_root_path.set(root_path)


def validate_path(path: str) -> str:
    """
    Validate and normalize file path within company/workspace boundary.

    Always validates against the root_path set in ContextVar, ensuring
    multi-tenant isolation at company/workspace level.

    Args:
        path: Requested file path (relative or absolute from workspace root)

    Returns:
        Normalized absolute path with company/workspace prefix

    Raises:
        ValueError: If path contains traversal attempts or is outside root_path
        RuntimeError: If root_path not set in context (middleware not configured)
    """
    if ".." in path or path.startswith("~"):
        raise ValueError(f"Path traversal not allowed: {path}")

    normalized = _normalize_path(path)
    root_path = get_gcs_root_path()
    root_normalized = _normalize_path(root_path)

    if normalized == "/":
        full_path = root_normalized.rstrip("/")
    else:
        full_path = root_normalized.rstrip("/") + normalized

    expected_prefix = root_normalized.rstrip("/") + "/"
    if not full_path.startswith(expected_prefix) and full_path != root_normalized.rstrip("/"):
        raise ValueError(
            f"Access denied: path '{path}' is outside root path '{root_path}'"
        )

    return full_path
