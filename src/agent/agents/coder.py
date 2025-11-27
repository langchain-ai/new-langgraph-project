"""Coder ReAct agent for database query execution."""
from langchain.agents import create_agent

from ..config.settings import claude
from ..tools.database import execute_query, test_database_connection
from ..utils.prompts import get_coder_prompt, get_prompt_and_resources
from .states import CoderState

coder_assistant = create_agent(
    model=claude.get_llm(),
    tools=[test_database_connection, execute_query],
    system_prompt=get_prompt_and_resources(get_coder_prompt, "coder.md"),
    state_schema=CoderState,
    name="coder_assistant",
)
