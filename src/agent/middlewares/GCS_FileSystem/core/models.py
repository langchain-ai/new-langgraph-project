from typing_extensions import TypedDict


class FileData(TypedDict):
    """Data structure for storing file contents with metadata."""
    content: list[str]
    created_at: str
    modified_at: str
