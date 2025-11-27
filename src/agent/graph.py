"""Auditor supervisor agent with coder assistant.

Multi-agent system for audit workflow automation.
"""
from langchain.agents import create_agent
from langchain_core.tools import tool

from .agents.coder import coder_assistant
from .agents.states import AuditorState
from .config.settings import claude
from .utils.prompts import get_auditor_prompt, get_prompt_and_resources


# Wrap the Coder agent as a tool for the supervisor
# This follows the official LangChain v1 supervisor pattern
@tool
async def transfer_to_coder(request: str) -> str:
    """Transfer to coder agent for database queries and technical operations.

    Use this when you need:
    - Database query execution
    - Audit test results retrieval
    - Technical data analysis
    - SQL operations on the PostgreSQL audit database

    The coder agent has access to database tools and can execute
    complex queries against the acr schema containing audit data.

    Args:
        request: Business-level instruction describing what data or
                analysis is needed. Should include:
                - Which audit test to run
                - Materiality thresholds or filters
                - Specific conditions or requirements
                Do NOT include SQL syntax.

    Returns:
        Structured technical results from the coder agent, including
        query results, analysis, and relevant context.
    """
    # Invoke the coder agent with the request
    result = await coder_assistant.ainvoke({
        "messages": [{"role": "user", "content": request}]
    })

    # Standard v1 pattern: Extract final message using .text property
    # This matches the official supervisor tutorial pattern
    return result["messages"][-1].text


# Create the auditor supervisor using LangChain v1 create_agent
# Note: LangGraph Server handles persistence automatically
# create_agent already returns a compiled graph, no need to call .compile() again
graph = create_agent(
    model=claude.get_llm(),
    tools=[transfer_to_coder],
    system_prompt=get_prompt_and_resources(get_auditor_prompt, "auditor.md"),
    state_schema=AuditorState,
    name="auditor",
)
