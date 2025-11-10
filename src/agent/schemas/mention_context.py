"""Pydantic schemas for mention context validation.

These schemas validate the structure and content of mention_context
to prevent security issues and ensure type safety.

Matches the backend API format from AE-AI AgentContextService.
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field, field_validator

# Size limits for DoS protection
MAX_FILES = 20  # Backend sends max 20 files
MAX_FOLDERS = 5
MAX_FILE_CONTENT_SIZE = 100000  # 100KB per file (backend sends summaries)
MAX_FOLDER_FILES_COMPLETE = 20  # Backend sends max 20 complete files per folder
MAX_FOLDER_FILES_REMAINING = 500  # Max metadata-only files
MAX_PATH_LENGTH = 1024


class FileMetadata(BaseModel):
    """Metadata for a file.

    Attributes:
        size_bytes: File size in bytes
        extension: File extension
        category: File category
        language: Document language
        confidence: OCR confidence score
        upload_date: Upload timestamp
        uploaded_by: User ID who uploaded
    """

    size_bytes: int | None = None
    extension: str | None = None
    category: str | None = None
    language: str | None = None
    confidence: float | None = None
    upload_date: str | None = None
    uploaded_by: int | None = None


class MentionFile(BaseModel):
    """File reference in mention context (backend format).

    Attributes:
        id: File ID from database
        name: File name
        path: Workspace-relative file path
        content: Pre-loaded file content (OCR summary or text)
        metadata: File metadata
    """

    id: int
    name: str
    path: str = Field(..., min_length=1, max_length=MAX_PATH_LENGTH)
    content: str = Field(default="", max_length=MAX_FILE_CONTENT_SIZE)
    metadata: FileMetadata | None = None

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

        # Check for absolute paths (workspace-relative only)
        if path.startswith("/") or path.startswith("~"):
            raise ValueError(f"Absolute paths not allowed: {path}")

        # Check for null bytes
        if "\0" in path:
            raise ValueError("Null bytes not allowed in path")

        return path


class FolderFileComplete(BaseModel):
    """Complete file info in folder (first 20 files).

    Attributes:
        id: File ID
        name: File name
        path: File path
        content: File content (OCR summary)
        metadata: File metadata
    """

    id: int
    name: str
    path: str
    content: str = Field(default="", max_length=MAX_FILE_CONTENT_SIZE)
    metadata: Dict[str, Any] | None = None


class FolderFileRemaining(BaseModel):
    """Metadata-only file info (files 21+).

    Attributes:
        id: File ID
        name: File name
        category: File category
        size_bytes: File size
    """

    id: int
    name: str
    category: str | None = None
    size_bytes: int | None = None


class FolderMetadata(BaseModel):
    """Folder metadata.

    Attributes:
        total_files: Total number of files in folder
        files_included: Number of files with full content
        files_metadata_only: Number of files with metadata only
        total_size_bytes: Total size of all files
    """

    total_files: int
    files_included: int
    files_metadata_only: int
    total_size_bytes: int | None = None


class MentionFolder(BaseModel):
    """Folder reference in mention context (backend format).

    Attributes:
        id: Folder ID from database
        name: Folder name
        files_complete: First 20 files with full content
        files_remaining: Remaining files (metadata only)
        metadata: Folder metadata
    """

    id: int
    name: str
    files_complete: List[FolderFileComplete] = Field(
        default_factory=list, max_length=MAX_FOLDER_FILES_COMPLETE
    )
    files_remaining: List[FolderFileRemaining] = Field(
        default_factory=list, max_length=MAX_FOLDER_FILES_REMAINING
    )
    metadata: FolderMetadata | None = None


class MentionContext(BaseModel):
    """Validated mention context structure (backend format).

    This schema enforces:
    - Maximum number of files (DoS protection)
    - Maximum number of folders (DoS protection)
    - Path security validation (prevents traversal)
    - Content size limits (prevents memory exhaustion)

    Attributes:
        files: List of mentioned files with pre-loaded content
        folders: List of mentioned folders with file listings
        warnings: List of warning messages (e.g., access denied)
    """

    files: List[MentionFile] = Field(default_factory=list, max_length=MAX_FILES)
    folders: List[MentionFolder] = Field(default_factory=list, max_length=MAX_FOLDERS)
    warnings: List[str] = Field(default_factory=list)

    def get_total_content_size(self) -> int:
        """Calculate total content size across all files.

        Returns:
            Total size in characters
        """
        total = sum(len(file.content) for file in self.files)

        # Add folder files content
        for folder in self.folders:
            total += sum(len(f.content) for f in folder.files_complete)

        return total
