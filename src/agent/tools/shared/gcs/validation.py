import logging
import os
import re

logger = logging.getLogger(__name__)

# GCS path format inside bucket: {company_slug}/{workspace_slug}/
GCS_PATH_PATTERN = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9\-_]{0,61}[a-zA-Z0-9])?/"
    r"[a-zA-Z0-9]([a-zA-Z0-9\-_]{0,61}[a-zA-Z0-9])?/?$"
)


def _normalize_path(path: str) -> str:
    """Normalize path to use forward slashes.

    Args:
        path: Path to normalize

    Returns:
        Normalized path with forward slashes
    """
    return os.path.normpath(path).replace("\\", "/")


def validate_root_path(root_path: str) -> None:
    """Validate GCS root path format.

    Args:
        root_path: Must be in format {company}/{workspace}/

    Raises:
        ValueError: If root_path format is invalid
    """
    if not GCS_PATH_PATTERN.match(root_path):
        logger.error(f"[GCSValidation] Invalid GCS path: {root_path}")
        raise ValueError(
            f"Invalid GCS root_path: '{root_path}'. "
            f"Expected format: {{company}}/{{workspace}}/ "
            f"(slugs: alphanumeric, hyphens, underscores, 1-63 chars)"
        )


def validate_path(path: str, root_path: str) -> str:
    """Validate and normalize file path within workspace boundary.

    Args:
        path: Requested file path (relative or absolute)
        root_path: GCS root path inside bucket ({company}/{workspace}/)

    Returns:
        Full GCS path with workspace prefix

    Raises:
        ValueError: If path contains traversal attempts or is outside root
    """
    logger.debug(f"[GCSValidation] Validating path: {path} with root: {root_path}")

    if ".." in path or path.startswith("~"):
        raise ValueError(f"Path traversal not allowed: {path}")

    # Normalize and clean path
    normalized = _normalize_path(path).lstrip("/")
    root_normalized = _normalize_path(root_path).rstrip("/")

    # Build full path
    if not normalized or normalized == ".":
        full_path = root_normalized
    else:
        full_path = f"{root_normalized}/{normalized}"

    # Ensure within root boundary
    if not full_path.startswith(root_normalized + "/") and full_path != root_normalized:
        raise ValueError(f"Access denied: '{path}' outside root '{root_path}'")

    logger.debug(f"[GCSValidation] Validated: {path} -> {full_path}")
    return full_path
