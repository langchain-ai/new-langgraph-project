"""Auditor supervisor agent with coder assistant.

Multi-agent system for audit workflow automation.
"""
from langgraph_supervisor import create_supervisor
from langgraph_supervisor.handoff import create_handoff_tool

from .agents.coder import coder_assistant
from .agents.states import AuditorState
from .config.settings import claude
from .utils.prompts import get_auditor_prompt, get_prompt_and_resources

# Create handoff tool for agent transfer
transfer_to_coder = create_handoff_tool(
    agent_name="coder_assistant",
    name="transfer_to_coder",
    description="Transfer to coder agent for database queries",
)

# Create the auditor supervisor graph
# Note: LangGraph Server handles persistence automatically
graph = create_supervisor(
    model=claude.get_llm(),
    agents=[coder_assistant],
    tools=[transfer_to_coder],
    state_schema=AuditorState,
    prompt=get_prompt_and_resources(get_auditor_prompt, "auditor.md"),
    output_mode="full_history",
    supervisor_name="auditor",
).compile(name="Auditor Agent")
