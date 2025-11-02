from google.api_core import retry
from google.api_core.exceptions import (
    DeadlineExceeded,
    InternalServerError,
    ServiceUnavailable,
)


MAX_LINE_LENGTH = 2000
LINE_NUMBER_WIDTH = 6
DEFAULT_READ_OFFSET = 0
DEFAULT_READ_LIMIT = 2000
EMPTY_CONTENT_WARNING = "System reminder: File exists but has empty contents"
CHARS_TO_TOKENS_RATIO = 4

GCS_RETRY = retry.Retry(
    initial=0.1,
    maximum=60.0,
    multiplier=2.0,
    timeout=300.0,
    predicate=retry.if_exception_type(
        ServiceUnavailable,
        DeadlineExceeded,
        InternalServerError,
    ),
)

GCS_SYSTEM_PROMPT = """## GCS Filesystem Tools `ls`, `read_file`, `write_file`, `edit_file`

You have access to a Google Cloud Storage filesystem which you can interact with using these tools.
All file paths must start with a /.

- ls: list all files in GCS
- read_file: read a file from GCS
- write_file: write to a file in GCS
- edit_file: edit a file in GCS

All files are stored persistently in Google Cloud Storage and will be available across conversations.

IMPORTANT: Your file access is restricted to the current company/workspace scope for security and multi-tenancy isolation.
You can only access files within your assigned workspace boundary."""

TOO_LARGE_TOOL_MSG = """Tool result too large, the result of this tool call {tool_call_id} was saved in GCS at this path: {file_path}
You can read the result from GCS by using the read_file tool, but make sure to only read part of the result at a time.
You can do this by specifying an offset and limit in the read_file tool call.
For example, to read the first 100 lines, you can use the read_file tool with offset=0 and limit=100.

Here are the first 10 lines of the result:
{content_sample}
"""

LS_TOOL_DESCRIPTION = """Lists all files in the GCS filesystem, optionally filtering by directory.

Usage:
- The ls tool will return a list of all files in GCS.
- You can optionally provide a path parameter to list files in a specific directory.
- This is very useful for exploring the file system and finding the right file to read or edit.
- You should almost ALWAYS use this tool before using the read_file or edit_file tools."""

READ_FILE_TOOL_DESCRIPTION = """Reads a file from GCS. You can access any file directly by using this tool.

Usage:
- The file_path parameter must be an absolute path, not a relative path
- By default, it reads up to 2000 lines starting from the beginning of the file
- You can optionally specify a line offset and limit (especially handy for long files)
- Any lines longer than 2000 characters will be truncated
- Results are returned using cat -n format, with line numbers starting at 1
- You can call multiple tools in a single response to read multiple files
- If you read a file that exists but has empty contents you will receive a system reminder warning
- You should ALWAYS make sure a file has been read before editing it."""

EDIT_FILE_TOOL_DESCRIPTION = """Performs exact string replacements in GCS files.

Usage:
- You must use your read_file tool at least once before editing
- When editing text from read_file output, preserve exact indentation as shown AFTER the line number prefix
- The line number prefix format is: spaces + line number + tab
- Never include the line number prefix in old_string or new_string
- ALWAYS prefer editing existing files. NEVER write new files unless explicitly required
- The edit will FAIL if old_string is not unique in the file
- Either provide more surrounding context or use replace_all=True to change all instances
- Use replace_all for renaming variables across the file."""

WRITE_FILE_TOOL_DESCRIPTION = """Writes to a new file in GCS.

Usage:
- The file_path parameter must be an absolute path, not a relative path
- The content parameter must be a string
- The write_file tool will create a new file
- Prefer to edit existing files over creating new ones when possible."""
