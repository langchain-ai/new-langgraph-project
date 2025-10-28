from .edit_file import gcs_edit_file_tool_generator
from .ls import gcs_ls_tool_generator
from .read_file import gcs_read_file_tool_generator
from .write_file import gcs_write_file_tool_generator

GCS_TOOL_GENERATORS = {
    "ls": gcs_ls_tool_generator,
    "read_file": gcs_read_file_tool_generator,
    "write_file": gcs_write_file_tool_generator,
    "edit_file": gcs_edit_file_tool_generator,
}

__all__ = [
    "GCS_TOOL_GENERATORS",
    "gcs_ls_tool_generator",
    "gcs_read_file_tool_generator",
    "gcs_write_file_tool_generator",
    "gcs_edit_file_tool_generator",
]
