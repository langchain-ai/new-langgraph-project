"""Middleware for emitting custom events during tool/sub-agent execution.

This middleware intercepts tool calls and emits custom events that can be
streamed to the frontend via the 'custom' stream mode, enabling real-time
UI updates for tool and sub-agent execution status.
"""

import logging
from typing import Any, Dict

from langchain.agents.middleware.types import AgentMiddleware, ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command

logger = logging.getLogger(__name__)


class EventTrackingMiddleware(AgentMiddleware):
    """Emit custom events when tools/sub-agents execute for real-time UI updates.

    This middleware intercepts tool calls and emits custom events that can be
    streamed to the frontend via the 'custom' stream mode.

    Events emitted:
    - tool_execution_starting: When a tool is about to execute
    - tool_execution_completed: When a tool finishes successfully
    - tool_execution_error: When a tool execution fails
    """

    def _extract_task_description(self, tool_call: Dict[str, Any]) -> str:
        """Extract task description from tool call arguments.

        For sub-agents, the 'description' field contains the task.
        For regular tools, we construct a description from the tool name.

        Args:
            tool_call: Tool call dictionary with name and args

        Returns:
            Human-readable task description
        """
        args = tool_call.get("args", {})

        # Sub-agents have 'description' in args
        if "description" in args:
            return args["description"]

        # For regular tools, use tool name
        tool_name = tool_call.get("name", "unknown")
        return f"Executing {tool_name}"

    def _is_subagent_call(self, tool_call: Dict[str, Any]) -> bool:
        """Check if this tool call is actually a sub-agent delegation.

        Args:
            tool_call: Tool call dictionary

        Returns:
            True if this is a sub-agent call, False otherwise
        """
        tool_name = tool_call.get("name", "")
        # Sub-agent middleware uses 'task' as tool name
        # and has 'subagent' in args
        return tool_name == "task" and "subagent" in tool_call.get("args", {})

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler,
    ) -> ToolMessage | Command:
        """Intercept tool execution to emit custom events.

        This runs BEFORE the tool executes, allowing us to emit
        'tool_execution_starting' event for real-time UI updates.

        Args:
            request: Tool call request with call dict, tool, state, and runtime
            handler: Async callable to execute the tool

        Returns:
            ToolMessage or Command from the tool execution
        """
        tool_call = request.tool_call
        tool_name = tool_call.get("name", "unknown")
        tool_call_id = tool_call.get("id", "")
        tool_args = tool_call.get("args", {})

        # Extract task description
        task_description = self._extract_task_description(tool_call)

        # Determine if this is a sub-agent
        is_subagent = self._is_subagent_call(tool_call)
        entity_type = "subagent" if is_subagent else "tool"

        # Extract subagent name if this is a subagent call
        subagent_name = tool_args.get("subagent") if is_subagent else None

        # Emit STARTING event via stream writer
        try:
            writer = request.runtime.stream_writer
            event_data = {
                "event": "tool_execution_starting",
                "entity_type": entity_type,
                "tool_name": tool_name,
                "tool_call_id": tool_call_id,
                "task_description": task_description,
                "tool_args": tool_args,
                "status": "running",
            }
            # Add subagent name if available
            if subagent_name:
                event_data["subagent_name"] = subagent_name

            writer(event_data)

            display_name = subagent_name if subagent_name else tool_name
            logger.info(f"[EventTracking] 🔄 {entity_type.capitalize()} starting: {display_name}")
        except Exception as e:
            logger.warning(f"[EventTracking] Failed to emit starting event: {e}")

        # Execute the actual tool
        try:
            result = await handler(request)

            # Emit COMPLETED event
            try:
                writer = request.runtime.stream_writer
                event_data = {
                    "event": "tool_execution_completed",
                    "entity_type": entity_type,
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "status": "completed",
                    # Include truncated result for debugging (optional)
                    "result_preview": str(result.content)[:200]
                    if hasattr(result, "content")
                    else None,
                }
                # Add subagent name if available
                if subagent_name:
                    event_data["subagent_name"] = subagent_name

                writer(event_data)

                display_name = subagent_name if subagent_name else tool_name
                logger.info(f"[EventTracking] ✅ {entity_type.capitalize()} completed: {display_name}")
            except Exception as e:
                logger.warning(f"[EventTracking] Failed to emit completed event: {e}")

            return result

        except Exception as error:
            # Emit ERROR event
            try:
                writer = request.runtime.stream_writer
                event_data = {
                    "event": "tool_execution_error",
                    "entity_type": entity_type,
                    "tool_name": tool_name,
                    "tool_call_id": tool_call_id,
                    "status": "error",
                    "error_message": str(error),
                }
                # Add subagent name if available
                if subagent_name:
                    event_data["subagent_name"] = subagent_name

                writer(event_data)

                display_name = subagent_name if subagent_name else tool_name
                logger.error(
                    f"[EventTracking] ❌ {entity_type.capitalize()} error: {display_name} - {error}"
                )
            except Exception as e:
                logger.warning(f"[EventTracking] Failed to emit error event: {e}")

            # Re-raise original error
            raise

    def wrap_tool_call(self, request: ToolCallRequest, handler) -> ToolMessage | Command:
        """Sync version (not implemented - use async version).

        Raises:
            NotImplementedError: Always raises as only async version is supported
        """
        raise NotImplementedError(
            "EventTrackingMiddleware only supports async execution. "
            "Use ainvoke() or astream() instead of invoke() or stream()."
        )
