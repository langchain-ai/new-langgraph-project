from typing import Optional

from langchain_core.tools import BaseTool, tool

from .config import EDIT_FILE_TOOL_DESCRIPTION, GCS_RETRY
from src.agent.tools.shared.gcs.client import get_gcs_client
from src.agent.tools.shared.gcs.file_operations import (
    file_data_to_gcs,
    file_data_to_string,
    gcs_blob_to_file_data,
    update_file_data,
    upload_blob_with_optimistic_locking,
)
from src.agent.tools.shared.gcs.validation import validate_path


def gcs_edit_file_tool_generator(
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
        file_path = validate_path(file_path)
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path.lstrip("/"))

        @GCS_RETRY
        def _reload_blob():
            blob.reload()

        _reload_blob()

        if not blob.exists():
            return f"Error: File '{file_path}' not found"

        current_generation = blob.generation

        file_data = gcs_blob_to_file_data(blob)
        content = file_data_to_string(file_data)

        occurrences = content.count(old_string)
        if occurrences == 0:
            return f"Error: String not found in file: '{old_string}'"

        if occurrences > 1 and not replace_all:
            return f"Error: String '{old_string}' appears {occurrences} times in file. Use replace_all=True to replace all instances, or provide a more specific string with surrounding context."

        new_content = content.replace(old_string, new_string)
        new_file_data = update_file_data(file_data, new_content)
        content_str, metadata = file_data_to_gcs(new_file_data)

        success = upload_blob_with_optimistic_locking(
            blob, content_str, metadata, expected_generation=current_generation
        )

        if not success:
            return f"Error: File '{file_path}' was modified by another process during edit. Please retry the operation."

        return f"Successfully replaced {occurrences} instance(s) of the string in '{file_path}'"

    return edit_file
