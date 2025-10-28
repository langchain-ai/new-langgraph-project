from typing import Optional

from ..config import EMPTY_CONTENT_WARNING, LINE_NUMBER_WIDTH, MAX_LINE_LENGTH


def format_content_with_line_numbers(
    content: str | list[str],
    start_line: int = 1,
) -> str:
    """Format file content with line numbers (tab format)."""
    if isinstance(content, str):
        lines = content.split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
    else:
        lines = content

    return "\n".join(
        f"{i + start_line:{LINE_NUMBER_WIDTH}d}\t{line[:MAX_LINE_LENGTH]}"
        for i, line in enumerate(lines)
    )


def split_content_into_lines(content: str | list[str]) -> list[str]:
    """Split content into lines with maximum length enforcement."""
    lines = content.split("\n") if isinstance(content, str) else content
    return [
        line[i:i+MAX_LINE_LENGTH]
        for line in lines
        for i in range(0, len(line) or 1, MAX_LINE_LENGTH)
    ]


def check_empty_content(content: str) -> Optional[str]:
    """Check if content is empty and return warning message."""
    if not content or content.strip() == "":
        return EMPTY_CONTENT_WARNING
    return None
