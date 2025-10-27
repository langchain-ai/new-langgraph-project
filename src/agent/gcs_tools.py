import json
import os
import time
from datetime import UTC, datetime
from functools import lru_cache
from typing import Optional

from google.api_core import retry
from google.api_core.exceptions import (
    DeadlineExceeded,
    InternalServerError,
    PreconditionFailed,
    ServiceUnavailable,
)
from google.cloud import storage
from google.oauth2 import service_account
from langchain_core.tools import BaseTool, tool
from typing_extensions import TypedDict


MAX_LINE_LENGTH = 2000
LINE_NUMBER_WIDTH = 6
DEFAULT_READ_OFFSET = 0
DEFAULT_READ_LIMIT = 2000
EMPTY_CONTENT_WARNING = "System reminder: File exists but has empty contents"

# Retry strategy for GCS operations
GCS_RETRY = retry.Retry(
    initial=0.1,
    maximum=60.0,
    multiplier=2.0,
    timeout=300.0,
    predicate=retry.if_exception_type(
        ServiceUnavailable,
        DeadlineExceeded,
        InternalServerError,
    ),
)


class FileData(TypedDict):
    """Data structure for storing file contents with metadata."""
    content: list[str]
    created_at: str
    modified_at: str


@lru_cache(maxsize=1)
def _get_gcs_client():
    """Get cached GCS client from GOOGLE_CLOUD_CREDENTIALS_JSON env var."""
    creds_json = os.getenv("GOOGLE_CLOUD_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError(
            "GOOGLE_CLOUD_CREDENTIALS_JSON environment variable not set. "
            "Set it to your service account JSON credentials."
        )

    info = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(info)
    return storage.Client(credentials=credentials)


def _validate_path(path: str) -> str:
    """Validate and normalize file path."""
    if ".." in path or path.startswith("~"):
        raise ValueError(f"Path traversal not allowed: {path}")

    normalized = os.path.normpath(path)
    normalized = normalized.replace("\\", "/")

    if not normalized.startswith("/"):
        normalized = f"/{normalized}"

    return normalized


def _format_content_with_line_numbers(
    content: str | list[str],
    start_line: int = 1,
) -> str:
    """Format file content with line numbers (tab format)."""
    if isinstance(content, str):
        lines = content.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
    else:
        lines = content

    return "\n".join(
        f"{i + start_line:{LINE_NUMBER_WIDTH}d}\t{line[:MAX_LINE_LENGTH]}"
        for i, line in enumerate(lines)
    )


def _split_content_into_lines(content: str | list[str]) -> list[str]:
    """Split content into lines with maximum length enforcement."""
    lines = content.split("\n") if isinstance(content, str) else content
    return [
        line[i:i+MAX_LINE_LENGTH]
        for line in lines
        for i in range(0, len(line) or 1, MAX_LINE_LENGTH)
    ]


def _create_file_data(content: str | list[str], created_at: Optional[str] = None) -> FileData:
    """Create FileData object with timestamps."""
    lines = _split_content_into_lines(content)
    now = datetime.now(UTC).isoformat()

    return {
        "content": lines,
        "created_at": created_at or now,
        "modified_at": now,
    }


def _update_file_data(file_data: FileData, content: str | list[str]) -> FileData:
    """Update FileData preserving creation timestamp."""
    lines = _split_content_into_lines(content)
    now = datetime.now(UTC).isoformat()

    return {
        "content": lines,
        "created_at": file_data["created_at"],
        "modified_at": now,
    }


def _file_data_to_string(file_data: FileData) -> str:
    """Convert FileData to plain string content."""
    return "\n".join(file_data["content"])


def _check_empty_content(content: str) -> Optional[str]:
    """Check if content is empty and return warning message."""
    if not content or content.strip() == "":
        return EMPTY_CONTENT_WARNING
    return None


def _file_data_to_gcs(file_data: FileData) -> tuple[str, dict]:
    """Convert FileData to GCS blob content and metadata."""
    content = _file_data_to_string(file_data)
    metadata = {
        "created_at": file_data["created_at"],
        "modified_at": file_data["modified_at"],
    }
    return content, metadata


def _gcs_blob_to_file_data(blob) -> FileData:
    """Convert GCS blob to FileData with retry logic."""
    content = GCS_RETRY(blob.download_as_text)()
    metadata = blob.metadata or {}

    return _create_file_data(
        content,
        created_at=metadata.get("created_at")
    )


def _upload_blob_with_retry(blob, content: str, metadata: dict):
    """Upload blob with automatic retry on transient failures."""
    blob.metadata = metadata

    @GCS_RETRY
    def _upload():
        blob.upload_from_string(content, content_type="text/plain")

    _upload()


def _upload_blob_with_optimistic_locking(
    blob,
    content: str,
    metadata: dict,
    expected_generation: Optional[int] = None,
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


# Tool descriptions
LS_TOOL_DESCRIPTION = """Lists all files in the GCS filesystem, optionally filtering by directory.

Usage:
- The ls tool will return a list of all files in GCS.
- You can optionally provide a path parameter to list files in a specific directory.
- This is very useful for exploring the file system and finding the right file to read or edit.
- You should almost ALWAYS use this tool before using the read_file or edit_file tools."""

READ_FILE_TOOL_DESCRIPTION = """Reads a file from GCS. You can access any file directly by using this tool.

Usage:
- The file_path parameter must be an absolute path, not a relative path
- By default, it reads up to 2000 lines starting from the beginning of the file
- You can optionally specify a line offset and limit (especially handy for long files)
- Any lines longer than 2000 characters will be truncated
- Results are returned using cat -n format, with line numbers starting at 1
- You can call multiple tools in a single response to read multiple files
- If you read a file that exists but has empty contents you will receive a system reminder warning
- You should ALWAYS make sure a file has been read before editing it."""

EDIT_FILE_TOOL_DESCRIPTION = """Performs exact string replacements in GCS files.

Usage:
- You must use your read_file tool at least once before editing
- When editing text from read_file output, preserve exact indentation as shown AFTER the line number prefix
- The line number prefix format is: spaces + line number + tab
- Never include the line number prefix in old_string or new_string
- ALWAYS prefer editing existing files. NEVER write new files unless explicitly required
- The edit will FAIL if old_string is not unique in the file
- Either provide more surrounding context or use replace_all=True to change all instances
- Use replace_all for renaming variables across the file."""

WRITE_FILE_TOOL_DESCRIPTION = """Writes to a new file in GCS.

Usage:
- The file_path parameter must be an absolute path, not a relative path
- The content parameter must be a string
- The write_file tool will create a new file
- Prefer to edit existing files over creating new ones when possible."""


def _gcs_ls_tool_generator(
    bucket_name: str,
    custom_description: Optional[str] = None,
) -> BaseTool:
    """Generate the GCS ls (list files) tool."""
    description = custom_description or LS_TOOL_DESCRIPTION

    @tool(description=description)
    def ls(path: Optional[str] = None, max_results: int = 1000) -> list[str]:
        client = _get_gcs_client()
        bucket = client.bucket(bucket_name)

        prefix = ""
        if path:
            normalized = _validate_path(path)
            prefix = normalized.lstrip("/")
            if prefix and not prefix.endswith("/"):
                prefix += "/"

        @GCS_RETRY
        def _list_blobs():
            return bucket.list_blobs(
                prefix=prefix,
                delimiter="/",
                max_results=max_results
            )

        iterator = _list_blobs()

        files = [f"/{blob.name}" for blob in iterator]
        directories = [f"/{prefix}" for prefix in iterator.prefixes]

        return files + directories

    return ls


def _gcs_read_file_tool_generator(
    bucket_name: str,
    custom_description: Optional[str] = None,
) -> BaseTool:
    """Generate the GCS read_file tool."""
    description = custom_description or READ_FILE_TOOL_DESCRIPTION

    @tool(description=description)
    def read_file(
        file_path: str,
        offset: int = DEFAULT_READ_OFFSET,
        limit: int = DEFAULT_READ_LIMIT,
    ) -> str:
        file_path = _validate_path(file_path)
        client = _get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path.lstrip("/"))

        @GCS_RETRY
        def _check_exists():
            return blob.exists()

        if not _check_exists():
            return f"Error: File '{file_path}' not found"

        file_data = _gcs_blob_to_file_data(blob)
        content = _file_data_to_string(file_data)

        empty_msg = _check_empty_content(content)
        if empty_msg:
            return empty_msg

        lines = content.splitlines()
        start_idx = offset
        end_idx = min(start_idx + limit, len(lines))

        if start_idx >= len(lines):
            return f"Error: Line offset {offset} exceeds file length ({len(lines)} lines)"

        selected_lines = lines[start_idx:end_idx]
        return _format_content_with_line_numbers(selected_lines, start_line=start_idx + 1)

    return read_file


def _gcs_write_file_tool_generator(
    bucket_name: str,
    custom_description: Optional[str] = None,
) -> BaseTool:
    """Generate the GCS write_file tool."""
    description = custom_description or WRITE_FILE_TOOL_DESCRIPTION

    @tool(description=description)
    def write_file(file_path: str, content: str) -> str:
        file_path = _validate_path(file_path)
        client = _get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path.lstrip("/"))

        @GCS_RETRY
        def _check_exists():
            return blob.exists()

        if _check_exists():
            return f"Cannot write to {file_path} because it already exists. Read and then make an edit, or write to a new path."

        file_data = _create_file_data(content)
        content_str, metadata = _file_data_to_gcs(file_data)

        _upload_blob_with_retry(blob, content_str, metadata)

        return f"Updated file {file_path}"

    return write_file


def _gcs_edit_file_tool_generator(
    bucket_name: str,
    custom_description: Optional[str] = None,
) -> BaseTool:
    """Generate the GCS edit_file tool."""
    description = custom_description or EDIT_FILE_TOOL_DESCRIPTION

    @tool(description=description)
    def edit_file(
        file_path: str,
        old_string: str,
        new_string: str,
        replace_all: bool = False,
    ) -> str:
        file_path = _validate_path(file_path)
        client = _get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path.lstrip("/"))

        @GCS_RETRY
        def _reload_blob():
            blob.reload()

        _reload_blob()

        if not blob.exists():
            return f"Error: File '{file_path}' not found"

        current_generation = blob.generation

        file_data = _gcs_blob_to_file_data(blob)
        content = _file_data_to_string(file_data)

        occurrences = content.count(old_string)
        if occurrences == 0:
            return f"Error: String not found in file: '{old_string}'"

        if occurrences > 1 and not replace_all:
            return f"Error: String '{old_string}' appears {occurrences} times in file. Use replace_all=True to replace all instances, or provide a more specific string with surrounding context."

        new_content = content.replace(old_string, new_string)
        new_file_data = _update_file_data(file_data, new_content)
        content_str, metadata = _file_data_to_gcs(new_file_data)

        success = _upload_blob_with_optimistic_locking(
            blob, content_str, metadata, expected_generation=current_generation
        )

        if not success:
            return f"Error: File '{file_path}' was modified by another process during edit. Please retry the operation."

        return f"Successfully replaced {occurrences} instance(s) of the string in '{file_path}'"

    return edit_file


GCS_TOOL_GENERATORS = {
    "ls": _gcs_ls_tool_generator,
    "read_file": _gcs_read_file_tool_generator,
    "write_file": _gcs_write_file_tool_generator,
    "edit_file": _gcs_edit_file_tool_generator,
}