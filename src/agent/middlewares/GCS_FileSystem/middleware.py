import os
from collections.abc import Awaitable, Callable
from typing import Any, Optional

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command

from .config import CHARS_TO_TOKENS_RATIO, GCS_SYSTEM_PROMPT, TOO_LARGE_TOOL_MSG
from .core.client import get_gcs_client
from .core.file_operations import create_file_data, file_data_to_gcs, upload_blob_with_retry
from .tools import GCS_TOOL_GENERATORS
from .utils.formatting import format_content_with_line_numbers


class GCSFilesystemMiddleware(AgentMiddleware):
    """
    Middleware for providing GCS filesystem tools to an agent.

    This middleware adds four GCS filesystem tools to the agent:
    ls, read_file, write_file, and edit_file.

    All files are stored persistently in Google Cloud Storage.
    """

    def __init__(
        self,
        *,
        bucket_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        custom_tool_descriptions: Optional[dict[str, str]] = None,
        tool_token_limit_before_evict: Optional[int] = 20000,
    ):
        """
        Initialize GCS filesystem middleware.

        Requires GOOGLE_CLOUD_CREDENTIALS_JSON env var with service account JSON.

        Args:
            bucket_name: GCS bucket name (defaults to GCS_BUCKET_NAME env var)
            system_prompt: Optional custom system prompt override
            custom_tool_descriptions: Optional custom tool descriptions override
            tool_token_limit_before_evict: Token limit before evicting tool result to GCS
        """
        self.bucket_name = bucket_name or os.getenv("GCS_BUCKET_NAME")
        if not self.bucket_name:
            raise ValueError(
                "GCS bucket name not provided. Set GCS_BUCKET_NAME env var or pass bucket_name parameter."
            )

        self.tool_token_limit_before_evict = tool_token_limit_before_evict
        self.system_prompt = system_prompt or GCS_SYSTEM_PROMPT
        self._bucket_validated = False

        self.tools = self._get_gcs_tools(custom_tool_descriptions or {})

    def _get_gcs_tools(self, custom_tool_descriptions: dict[str, str]) -> list:
        """Generate GCS tools using tool generators."""
        tools = []
        for tool_name, tool_generator in GCS_TOOL_GENERATORS.items():
            tool = tool_generator(
                bucket_name=self.bucket_name,
                custom_description=custom_tool_descriptions.get(tool_name),
            )
            tools.append(tool)
        return tools

    def _validate_bucket_once(self):
        """Validate bucket access only once per middleware instance."""
        if self._bucket_validated:
            return

        try:
            client = get_gcs_client()
            bucket = client.bucket(self.bucket_name)
            bucket.reload(timeout=5)
            self._bucket_validated = True
        except Exception as e:
            raise ValueError(
                f"Cannot access GCS bucket '{self.bucket_name}': {e}"
            ) from e

    def before_agent(
        self, state: AgentState, runtime: Runtime[Any]
    ) -> dict[str, Any] | None:
        """Validate GCS bucket access before agent execution (cached)."""
        self._validate_bucket_once()
        return None

    def _update_system_prompt(self, request: ModelRequest) -> None:
        """Update request with GCS system prompt."""
        if self.system_prompt:
            request.system_prompt = (
                f"{request.system_prompt}\n\n{self.system_prompt}"
                if request.system_prompt
                else self.system_prompt
            )

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Update the system prompt to include GCS filesystem instructions."""
        self._update_system_prompt(request)
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """(async) Update the system prompt to include GCS filesystem instructions."""
        self._update_system_prompt(request)
        return await handler(request)

    def _should_bypass_interception(self, request: ToolCallRequest) -> bool:
        """Check if tool call should bypass size interception."""
        return (
            self.tool_token_limit_before_evict is None
            or request.tool_call["name"] in GCS_TOOL_GENERATORS
        )

    def _intercept_large_tool_result(
        self, tool_result: ToolMessage | Command
    ) -> ToolMessage | Command:
        """Intercept large tool results and save to GCS."""
        if isinstance(tool_result, ToolMessage) and isinstance(
            tool_result.content, str
        ):
            content = tool_result.content
            if (
                self.tool_token_limit_before_evict
                and len(content) > CHARS_TO_TOKENS_RATIO * self.tool_token_limit_before_evict
            ):
                file_path = f"/large_tool_results/{tool_result.tool_call_id}"

                client = get_gcs_client()
                bucket = client.bucket(self.bucket_name)
                blob = bucket.blob(file_path.lstrip("/"))

                file_data = create_file_data(content)
                content_str, metadata = file_data_to_gcs(file_data)

                upload_blob_with_retry(blob, content_str, metadata)

                return ToolMessage(
                    TOO_LARGE_TOOL_MSG.format(
                        tool_call_id=tool_result.tool_call_id,
                        file_path=file_path,
                        content_sample=format_content_with_line_numbers(
                            file_data["content"][:10], start_line=1
                        ),
                    ),
                    tool_call_id=tool_result.tool_call_id,
                )

        return tool_result

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        """Check size of tool result and evict to GCS if too large."""
        if self._should_bypass_interception(request):
            return handler(request)

        tool_result = handler(request)
        return self._intercept_large_tool_result(tool_result)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        """(async) Check size of tool result and evict to GCS if too large."""
        if self._should_bypass_interception(request):
            return await handler(request)

        tool_result = await handler(request)
        return self._intercept_large_tool_result(tool_result)
