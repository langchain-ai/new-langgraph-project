"""Pydantic schemas for mention context validation.

These schemas validate the structure and content of mention_context
to prevent security issues and ensure type safety.
"""

from typing import List

from pydantic import BaseModel, Field, field_validator

# Size limits for DoS protection
MAX_FILES = 10
MAX_FOLDERS = 5
MAX_FILE_CONTENT_SIZE = 10000  # 10KB per file
MAX_FOLDER_FILES = 100  # Max files to list per folder
MAX_PATH_LENGTH = 1024


class MentionFile(BaseModel):
    """File reference in mention context.

    Attributes:
        path: Workspace-relative file path
        content: Pre-loaded file content (OCR summary or text)
    """

    path: str = Field(..., min_length=1, max_length=MAX_PATH_LENGTH)
    content: str = Field(default="", max_length=MAX_FILE_CONTENT_SIZE)

    @field_validator("path")
    @classmethod
    def validate_path_security(cls, v: str) -> str:
        """Validate path doesn't contain traversal patterns.

        Args:
            v: Path to validate

        Returns:
            Validated path

        Raises:
            ValueError: If path contains traversal patterns
        """
        path = v.strip()

        # Check for path traversal
        if ".." in path:
            raise ValueError(f"Path traversal not allowed: {path}")

        # Check for absolute paths
        if path.startswith("/") or path.startswith("~"):
            raise ValueError(f"Absolute paths not allowed: {path}")

        # Check for null bytes
        if "\0" in path:
            raise ValueError("Null bytes not allowed in path")

        return path


class MentionFolder(BaseModel):
    """Folder reference in mention context.

    Attributes:
        path: Workspace-relative folder path
        files: List of files in the folder
    """

    path: str = Field(..., min_length=1, max_length=MAX_PATH_LENGTH)
    files: List[str] = Field(default_factory=list, max_length=MAX_FOLDER_FILES)

    @field_validator("path")
    @classmethod
    def validate_path_security(cls, v: str) -> str:
        """Validate path doesn't contain traversal patterns.

        Args:
            v: Path to validate

        Returns:
            Validated path

        Raises:
            ValueError: If path contains traversal patterns
        """
        path = v.strip()

        # Check for path traversal
        if ".." in path:
            raise ValueError(f"Path traversal not allowed: {path}")

        # Check for absolute paths
        if path.startswith("/") or path.startswith("~"):
            raise ValueError(f"Absolute paths not allowed: {path}")

        # Check for null bytes
        if "\0" in path:
            raise ValueError("Null bytes not allowed in path")

        return path


class MentionContext(BaseModel):
    """Validated mention context structure.

    This schema enforces:
    - Maximum number of files (DoS protection)
    - Maximum number of folders (DoS protection)
    - Path security validation (prevents traversal)
    - Content size limits (prevents memory exhaustion)

    Attributes:
        files: List of mentioned files with pre-loaded content
        folders: List of mentioned folders with file listings
    """

    files: List[MentionFile] = Field(default_factory=list, max_length=MAX_FILES)
    folders: List[MentionFolder] = Field(default_factory=list, max_length=MAX_FOLDERS)

    def get_total_content_size(self) -> int:
        """Calculate total content size across all files.

        Returns:
            Total size in characters
        """
        return sum(len(file.content) for file in self.files)
