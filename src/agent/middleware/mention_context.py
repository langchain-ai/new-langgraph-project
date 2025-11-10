r"""Middleware to enrich system prompt with mention context.

This middleware implements the @[filename] mention system by reading
pre-loaded file/folder content from state and injecting it into the
system prompt before model execution.

The frontend sends mention_context via config.configurable, which is
extracted by ConfigToStateMiddleware and stored in state. This middleware
then reads it and builds an enriched system prompt.

Flow:
1. ConfigToStateMiddleware extracts mention_context → state
2. MentionContextMiddleware reads state["mention_context"]
3. Builds enriched prompt with file/folder contents
4. Modifies request.system_prompt in-place
5. Model receives enriched prompt

Example mention_context structure:
{
    "files": [
        {"path": "docs/report.pdf", "content": "Summary: ..."},
        {"path": "data/sales.csv", "content": "Product,Sales\n..."}
    ],
    "folders": [
        {"path": "projects/Q4/", "files": ["file1.txt", "file2.md"]}
    ]
}
"""

import logging
import re
from typing import Callable

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)

from src.agent.schemas.mention_context import MentionContext

logger = logging.getLogger(__name__)

# Display limits for prompt formatting
MAX_FILE_CONTENT_DISPLAY = 15000  # Characters per file
MAX_FOLDER_FILES_DISPLAY = 50  # Files to show per folder

# Prompt injection patterns to detect
DANGEROUS_PATTERNS = [
    r"ignore\s+all\s+previous\s+instructions",
    r"system\s*:\s*you\s+are",
    r"override\s+system",
    r"developer\s+mode",
    r"admin\s+mode",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
]


class MentionContextMiddleware(AgentMiddleware):
    """Enrich system prompt with file/folder content from mentions.

    Uses wrap_model_call hook to modify system prompt before model execution.
    Reads mention_context from state (populated by ConfigToStateMiddleware).

    The enriched prompt includes file contents and folder listings from
    @[filename] mentions in the user's message.

    Security features:
    - Prompt injection detection and sanitization
    - Path sanitization to prevent markdown breakout
    - Content size validation
    - Graceful error handling
    """

    def _enrich_prompt(
        self,
        request: ModelRequest,
    ) -> None:
        """Enrich system prompt with mention context (shared logic).

        Args:
            request: Model request to modify in-place
        """
        mention_context = request.state.get("mention_context")

        if not mention_context:
            # No mention context, skip enrichment
            return

        # Type check (should be MentionContext from ConfigToStateMiddleware)
        if not isinstance(mention_context, MentionContext):
            logger.error(
                f"[MentionContext] Invalid type: {type(mention_context)}, "
                "expected MentionContext"
            )
            # Skip enrichment
            return

        if not mention_context.files and not mention_context.folders:
            # Empty mention context
            return

        # Build enriched prompt with sanitization
        enriched_prompt = self._build_enriched_prompt(
            request.system_prompt, mention_context
        )

        # Modify request in-place
        request.system_prompt = enriched_prompt

        logger.info("[MentionContext] Enriched prompt with mention context")

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Enrich system prompt with mention context before model call (sync).

        Args:
            request: Model request with state containing mention_context
            handler: Handler to execute model request

        Returns:
            Model response from handler
        """
        try:
            self._enrich_prompt(request)
            return handler(request)
        except Exception as e:
            # Log error but don't crash - graceful degradation
            logger.error(
                f"[MentionContext] Failed to enrich prompt: {e}", exc_info=True
            )
            # Continue without enrichment
            return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Enrich system prompt with mention context before model call (async).

        Args:
            request: Model request with state containing mention_context
            handler: Async handler to execute model request

        Returns:
            Model response from handler
        """
        try:
            self._enrich_prompt(request)
            return await handler(request)
        except Exception as e:
            # Log error but don't crash - graceful degradation
            logger.error(
                f"[MentionContext] Failed to enrich prompt: {e}", exc_info=True
            )
            # Continue without enrichment
            return await handler(request)

    def _sanitize_path(self, path: str) -> str:
        """Sanitize path for safe display in prompt.

        Args:
            path: File or folder path

        Returns:
            Sanitized path safe for markdown display
        """
        if not path:
            return "unknown"

        # Remove newlines and carriage returns
        sanitized = path.replace("\n", "").replace("\r", "")

        # Remove markdown special characters that could break formatting
        sanitized = sanitized.replace("```", "").replace("**", "")
        sanitized = sanitized.replace("`", "")

        # Limit length to prevent excessively long paths
        if len(sanitized) > 500:
            sanitized = sanitized[:500] + "..."

        return sanitized

    def _sanitize_file_content(self, content: str, path: str) -> str:
        """Sanitize file content to prevent prompt injection.

        Args:
            content: File content
            path: File path (for logging)

        Returns:
            Sanitized content safe for prompt injection
        """
        if not content:
            return ""

        # Check for dangerous patterns
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                logger.warning(
                    f"[MentionContext] Suspicious pattern detected in {path}, "
                    "content sanitized"
                )
                # Replace dangerous patterns with safe text
                content = re.sub(pattern, "[REDACTED]", content, flags=re.IGNORECASE)

        # Escape markdown code fences to prevent breakout
        content = content.replace("```", "\\`\\`\\`")

        # Truncate if needed (additional safety layer)
        if len(content) > MAX_FILE_CONTENT_DISPLAY:
            content = (
                content[:MAX_FILE_CONTENT_DISPLAY]
                + f"\n... (truncated, {len(content)} total characters)"
            )

        return content

    def _build_enriched_prompt(
        self, base_prompt: str | None, mention_context: MentionContext
    ) -> str:
        """Build enriched prompt with mention context.

        Args:
            base_prompt: Original system prompt
            mention_context: Validated context with files and folders

        Returns:
            Enriched system prompt with sanitized file/folder contents
        """
        base = base_prompt or ""
        context_parts = []

        # Add file contents
        if mention_context.files:
            context_parts.append("\n## Referenced Files\n")
            context_parts.append(
                "The user has mentioned the following files in their message. "
                "Use this content to answer their question:\n"
            )

            for file_info in mention_context.files:
                # Sanitize path for display
                path = self._sanitize_path(file_info.path)

                # Sanitize content for security
                content = self._sanitize_file_content(file_info.content, file_info.path)

                if content:
                    context_parts.append(f"\n**File: {path}**\n```\n{content}\n```\n")
                else:
                    context_parts.append(f"\n**File: {path}**\n(Empty file)\n")

        # Add folder information
        if mention_context.folders:
            context_parts.append("\n## Referenced Folders\n")
            context_parts.append(
                "The user has mentioned the following folders. "
                "These are the files contained in each folder:\n"
            )

            for folder_info in mention_context.folders:
                # Sanitize folder path for display
                path = self._sanitize_path(folder_info.path)

                if folder_info.files:
                    context_parts.append(f"\n**Folder: {path}**\n")
                    context_parts.append(f"Contains {len(folder_info.files)} files:\n")

                    # Limit display to first MAX_FOLDER_FILES_DISPLAY files
                    for file_path in folder_info.files[:MAX_FOLDER_FILES_DISPLAY]:
                        # Sanitize each file path in folder
                        sanitized_file = self._sanitize_path(file_path)
                        context_parts.append(f"  - {sanitized_file}\n")

                    if len(folder_info.files) > MAX_FOLDER_FILES_DISPLAY:
                        remaining = len(folder_info.files) - MAX_FOLDER_FILES_DISPLAY
                        context_parts.append(f"  ... and {remaining} more files\n")
                else:
                    context_parts.append(f"\n**Folder: {path}**\n(Empty folder)\n")

        # Combine base prompt with context
        if context_parts:
            context_section = "".join(context_parts)
            return f"{base}\n{context_section}"

        return base
