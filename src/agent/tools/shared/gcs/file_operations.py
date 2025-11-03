import time
from datetime import UTC, datetime

from google.api_core.exceptions import PreconditionFailed
from tenacity import retry, stop_after_attempt, wait_exponential

from .formatting import split_content_into_lines
from .models import FileData

# Define GCS_RETRY decorator here since it's needed by multiple modules
GCS_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
)


def create_file_data(content: str | list[str], created_at: str | None = None) -> FileData:
    """Create FileData object with timestamps."""
    lines = split_content_into_lines(content)
    now = datetime.now(UTC).isoformat()

    return {
        "content": lines,
        "created_at": created_at or now,
        "modified_at": now,
    }


def update_file_data(file_data: FileData, content: str | list[str]) -> FileData:
    """Update FileData preserving creation timestamp."""
    lines = split_content_into_lines(content)
    now = datetime.now(UTC).isoformat()

    return {
        "content": lines,
        "created_at": file_data["created_at"],
        "modified_at": now,
    }


def file_data_to_string(file_data: FileData) -> str:
    """Convert FileData to plain string content."""
    return "\n".join(file_data["content"])


def file_data_to_gcs(file_data: FileData) -> tuple[str, dict]:
    """Convert FileData to GCS blob content and metadata."""
    content = file_data_to_string(file_data)
    metadata = {
        "created_at": file_data["created_at"],
        "modified_at": file_data["modified_at"],
    }
    return content, metadata


def gcs_blob_to_file_data(blob) -> FileData:
    """Convert GCS blob to FileData with retry logic."""
    content = GCS_RETRY(blob.download_as_text)()
    metadata = blob.metadata or {}

    return create_file_data(
        content,
        created_at=metadata.get("created_at")
    )


def upload_blob_with_retry(blob, content: str, metadata: dict):
    """Upload blob with automatic retry on transient failures."""
    blob.metadata = metadata

    @GCS_RETRY
    def _upload():
        blob.upload_from_string(content, content_type="text/plain")

    _upload()


def upload_blob_with_optimistic_locking(
    blob,
    content: str,
    metadata: dict,
    expected_generation: int | None = None,
    max_retries: int = 3
) -> bool:
    """Upload blob with optimistic locking using generation matching.

    Args:
        blob: GCS blob object
        content: Content to upload
        metadata: Metadata to set
        expected_generation: Expected generation number (None for new files)
        max_retries: Maximum retry attempts on precondition failure

    Returns:
        True if upload succeeded, False if concurrent modification detected
    """
    blob.metadata = metadata

    for attempt in range(max_retries):
        try:
            if expected_generation is None:
                blob.upload_from_string(
                    content,
                    content_type="text/plain",
                    if_generation_match=0
                )
            else:
                blob.upload_from_string(
                    content,
                    content_type="text/plain",
                    if_generation_match=expected_generation
                )
            return True
        except PreconditionFailed:
            if attempt == max_retries - 1:
                return False
            time.sleep(0.1 * (2 ** attempt))

    return False
