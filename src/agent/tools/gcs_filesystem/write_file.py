from langchain_core.tools import tool

from .config import GCS_RETRY, WRITE_FILE_TOOL_DESCRIPTION
from .tool_utils import normalize_gcs_blob_path, setup_gcs_bucket
from src.agent.tools.shared.gcs.file_operations import create_file_data, file_data_to_gcs, upload_blob_with_retry
from src.agent.tools.shared.gcs.validation import validate_path


def gcs_write_file_tool_generator(bucket_name, custom_description=None):
    """Generate GCS write_file tool."""
    description = custom_description or WRITE_FILE_TOOL_DESCRIPTION

    @tool(description=description)
    def write_file(file_path, content):
        bucket = setup_gcs_bucket(bucket_name)
        file_path = validate_path(file_path)
        blob = bucket.blob(normalize_gcs_blob_path(file_path))

        @GCS_RETRY
        def _check_exists():
            return blob.exists()

        if _check_exists():
            return f"Cannot write to {file_path} because it already exists. Read and then make an edit, or write to a new path."

        file_data = create_file_data(content)
        content_str, metadata = file_data_to_gcs(file_data)

        upload_blob_with_retry(blob, content_str, metadata)

        return f"Updated file {file_path}"

    return write_file
