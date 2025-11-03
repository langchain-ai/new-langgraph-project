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

        # Remove root_path prefix to show workspace-relative paths
        root_prefix = normalize_gcs_blob_path(root_path)

        files = []
        for blob in iterator:
            # Remove root prefix to get workspace-relative path
            relative_path = blob.name
            if relative_path.startswith(root_prefix):
                relative_path = relative_path[len(root_prefix):]
            files.append(f"/{relative_path}" if relative_path else "/")

        directories = []
        for prefix_path in iterator.prefixes:
            # Remove root prefix to get workspace-relative path
            relative_path = prefix_path
            if relative_path.startswith(root_prefix):
                relative_path = relative_path[len(root_prefix):]
            directories.append(f"/{relative_path}" if relative_path else "/")

        return files + directories

    return ls
