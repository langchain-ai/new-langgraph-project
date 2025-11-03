import logging
import os
import re

logger = logging.getLogger(__name__)

COMPANY_WORKSPACE_PATTERN = re.compile(
    r"^/company-[a-zA-Z0-9]([a-zA-Z0-9\-_]{0,61}[a-zA-Z0-9])?/"
    r"workspace-[a-zA-Z0-9]([a-zA-Z0-9\-_]{0,61}[a-zA-Z0-9])?/?$"
)


def _normalize_path(path: str) -> str:
    """Normalize path to use forward slashes and ensure leading slash.

    Args:
        path: Path to normalize

    Returns:
        Normalized path with forward slashes and leading slash
    """
    normalized = os.path.normpath(path).replace("\\", "/")
    return f"/{normalized}" if not normalized.startswith("/") else normalized


def validate_root_path(root_path: str) -> None:
    """Validate GCS root path format.

    Args:
        root_path: Must be in format /company-{id}/workspace-{id}/

    Raises:
        ValueError: If root_path format is invalid
    """
    if not COMPANY_WORKSPACE_PATTERN.match(root_path):
        logger.error(f"[GCSValidation] Invalid path format: {root_path}")
        raise ValueError(
            f"Invalid root_path format: '{root_path}'. "
            f"Expected format: /company-{{id}}/workspace-{{id}}/ "
            f"(id: alphanumeric, hyphens, underscores only, 1-63 chars)"
        )


def validate_path(path: str, root_path: str) -> str:
    """Validate and normalize file path within company/workspace boundary.

    Args:
        path: Requested file path (relative or absolute from workspace root)
        root_path: GCS root path (from runtime.state)

    Returns:
        Normalized absolute path with company/workspace prefix

    Raises:
        ValueError: If path contains traversal attempts or is outside root_path
    """
    logger.debug(f"[GCSValidation] Validating path: {path} with root: {root_path}")

    if ".." in path or path.startswith("~"):
        logger.error(f"[GCSValidation] Path traversal attempt detected: {path}")
        raise ValueError(f"Path traversal not allowed: {path}")

    normalized = _normalize_path(path)
    root_normalized = _normalize_path(root_path)

    if normalized == "/":
        full_path = root_normalized.rstrip("/")
    else:
        full_path = root_normalized.rstrip("/") + normalized

    expected_prefix = root_normalized.rstrip("/") + "/"
    if not full_path.startswith(expected_prefix) and full_path != root_normalized.rstrip("/"):
        logger.error(f"[GCSValidation] Path outside root: {path} (root: {root_path})")
        raise ValueError(
            f"Access denied: path '{path}' is outside root path '{root_path}'"
        )

    logger.debug(f"[GCSValidation] Validated path: {path} -> {full_path}")
    return full_path
