"""Coder ReAct agent for database query execution."""
from langgraph.prebuilt import create_react_agent

from ..config.settings import claude
from ..tools.database import execute_query, test_database_connection
from ..utils.prompts import get_coder_prompt, get_prompt_and_resources
from .states import CoderState

coder_assistant = create_react_agent(
    model=claude.get_llm(),
    prompt=get_prompt_and_resources(get_coder_prompt, "coder.md"),
    state_schema=CoderState,
    name="coder_assistant",
    tools=[test_database_connection, execute_query],
)
