from langchain.tools import ToolRuntime
from langchain_core.tools import tool

from src.agent.tools.shared.gcs.file_operations import (
    file_data_to_string,
    gcs_blob_to_file_data,
)
from src.agent.tools.shared.gcs.formatting import (
    check_empty_content,
    format_content_with_line_numbers,
)
from src.agent.tools.shared.gcs.validation import validate_path

from .config import (
    DEFAULT_READ_LIMIT,
    DEFAULT_READ_OFFSET,
    GCS_RETRY,
    READ_FILE_TOOL_DESCRIPTION,
)
from .tool_utils import (
    get_root_path_from_runtime,
    normalize_gcs_blob_path,
    setup_gcs_bucket,
)


def gcs_read_file_tool_generator(bucket_name, custom_description=None):
    """Generate GCS read_file tool."""
    description = custom_description or READ_FILE_TOOL_DESCRIPTION

    @tool(description=description)
    def read_file(file_path, offset=DEFAULT_READ_OFFSET, limit=DEFAULT_READ_LIMIT, runtime: ToolRuntime = None):
        root_path = get_root_path_from_runtime(runtime)
        bucket = setup_gcs_bucket(bucket_name)
        file_path = validate_path(file_path, root_path)
        blob = bucket.blob(normalize_gcs_blob_path(file_path))

        @GCS_RETRY
        def _check_exists():
            return blob.exists()

        if not _check_exists():
            return f"Error: File '{file_path}' not found"

        file_data = gcs_blob_to_file_data(blob)
        content = file_data_to_string(file_data)

        empty_msg = check_empty_content(content)
        if empty_msg:
            return empty_msg

        lines = content.splitlines()
        start_idx = offset
        end_idx = min(start_idx + limit, len(lines))

        if start_idx >= len(lines):
            return f"Error: Line offset {offset} exceeds file length ({len(lines)} lines)"

        selected_lines = lines[start_idx:end_idx]
        return format_content_with_line_numbers(selected_lines, start_line=start_idx + 1)

    return read_file
