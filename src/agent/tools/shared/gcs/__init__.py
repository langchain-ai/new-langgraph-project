"""GCS shared utilities for tools.

Contains utilities for GCS client management, file operations, validation,
and formatting that are shared across GCS-related tools.
"""

# Client utilities
from .client import get_gcs_client

# File operation utilities
from .file_operations import (
    create_file_data,
    file_data_to_gcs,
    file_data_to_string,
    gcs_blob_to_file_data,
    update_file_data,
    upload_blob_with_optimistic_locking,
    upload_blob_with_retry,
)

# Formatting utilities
from .formatting import (
    check_empty_content,
    format_content_with_line_numbers,
    split_content_into_lines,
)

# Models
from .models import FileData

# Validation utilities
from .validation import (
    validate_path,
    validate_root_path,
)

__all__ = [
    # Client
    "get_gcs_client",
    # File operations
    "create_file_data",
    "file_data_to_gcs",
    "file_data_to_string",
    "gcs_blob_to_file_data",
    "update_file_data",
    "upload_blob_with_optimistic_locking",
    "upload_blob_with_retry",
    # Formatting
    "check_empty_content",
    "format_content_with_line_numbers",
    "split_content_into_lines",
    # Models
    "FileData",
    # Validation
    "validate_path",
    "validate_root_path",
]