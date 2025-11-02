"""GCS Filesystem Tools Module

Provides tools for interacting with Google Cloud Storage as a filesystem.
"""
from .edit_file import gcs_edit_file_tool_generator
from .ls import gcs_ls_tool_generator
from .read_file import gcs_read_file_tool_generator
from .write_file import gcs_write_file_tool_generator

# Tool generators for creating tool instances
GCS_TOOL_GENERATORS = {
    "ls": gcs_ls_tool_generator,
    "read_file": gcs_read_file_tool_generator,
    "write_file": gcs_write_file_tool_generator,
    "edit_file": gcs_edit_file_tool_generator,
}

def get_gcs_tools(bucket_name: str, custom_descriptions: dict = None):
    """Generate all GCS tools with the given configuration.

    Args:
        bucket_name: GCS bucket name
        custom_descriptions: Optional custom tool descriptions

    Returns:
        List of configured GCS tools
    """
    custom_descriptions = custom_descriptions or {}
    tools = []
    for tool_name, generator in GCS_TOOL_GENERATORS.items():
        tool = generator(
            bucket_name=bucket_name,
            custom_description=custom_descriptions.get(tool_name)
        )
        tools.append(tool)
    return tools

__all__ = [
    "GCS_TOOL_GENERATORS",
    "get_gcs_tools",
    "gcs_ls_tool_generator",
    "gcs_read_file_tool_generator",
    "gcs_write_file_tool_generator",
    "gcs_edit_file_tool_generator",
]