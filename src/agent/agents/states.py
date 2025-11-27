"""State schemas for Lucart Agents."""
from typing import Annotated, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AuditorState(TypedDict):
    """State schema for the Auditor supervisor agent."""

    messages: Annotated[List[BaseMessage], add_messages]
    remaining_steps: Optional[int]


class CoderState(TypedDict):
    """State schema for the Coder ReAct agent."""

    messages: Annotated[List[BaseMessage], add_messages]
    remaining_steps: Optional[int]
