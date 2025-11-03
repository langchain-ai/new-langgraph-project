from langchain.tools import ToolRuntime
from langchain_core.tools import tool

from src.agent.tools.shared.gcs.validation import validate_path

from .config import GCS_RETRY, LS_TOOL_DESCRIPTION
from .tool_utils import get_root_path_from_runtime, normalize_gcs_blob_path, setup_gcs_bucket


def gcs_ls_tool_generator(bucket_name, custom_description=None):
    """Generate GCS ls tool."""
    description = custom_description or LS_TOOL_DESCRIPTION

    @tool(description=description)
    def ls(path=None, max_results=1000, runtime: ToolRuntime = None):
        root_path = get_root_path_from_runtime(runtime)
        bucket = setup_gcs_bucket(bucket_name)

        prefix = ""
        if path:
            normalized = validate_path(path, root_path)
            prefix = normalize_gcs_blob_path(normalized)
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
