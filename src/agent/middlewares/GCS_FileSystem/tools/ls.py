from typing import Optional

from langchain_core.tools import BaseTool, tool

from ..config import GCS_RETRY, LS_TOOL_DESCRIPTION
from ..core.client import get_gcs_client
from ..utils.validation import validate_path


def gcs_ls_tool_generator(
    bucket_name: str,
    custom_description: Optional[str] = None,
) -> BaseTool:
    """Generate the GCS ls (list files) tool."""
    description = custom_description or LS_TOOL_DESCRIPTION

    @tool(description=description)
    def ls(path: Optional[str] = None, max_results: int = 1000) -> list[str]:
        client = get_gcs_client()
        bucket = client.bucket(bucket_name)

        prefix = ""
        if path:
            normalized = validate_path(path)
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
