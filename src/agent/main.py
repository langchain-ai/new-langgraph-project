"""Main agent configuration and initialization.

This module creates the main LangGraph agent with middleware stack including:
- ConfigToStateMiddleware: Extracts config to state for sub-agent access
- MentionContextMiddleware: Enriches prompt with @mention file/folder content
- SubAgentMiddleware: Delegates operations to specialized sub-agents
- Human-in-the-loop approval for write operations
"""

import os

from deepagents import SubAgentMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware
from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    TodoListMiddleware,
)
from langchain.agents.middleware.summarization import SummarizationMiddleware
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware

from src.agent.config.models_config import CLAUDE_HAIKU_4_5, CLAUDE_SONNET_4_5
from src.agent.middleware.config_to_state import ConfigToStateMiddleware
from src.agent.middleware.event_tracking import EventTrackingMiddleware
from src.agent.middleware.mention_context import MentionContextMiddleware
from src.agent.state import MainAgentState
from src.agent.sub_agents import get_subagents
from src.agent.tools.gcs_filesystem import gcs_ls_tool_generator

# Model Configuration
MAX_TOKENS_BEFORE_SUMMARY = 170000
MESSAGES_TO_KEEP = 6
RECURSION_LIMIT = 1000

# Prompts
BASE_AGENT_PROMPT = "In order to complete the objective that the user asks of you, you have access to a number of standard tools."
RESEARCH_INSTRUCTIONS = """
You are an expert financial advisor with access to company data and documents.

CRITICAL SECURITY REQUIREMENTS:
- You have access ONLY to the current workspace assigned to this session
- NEVER mention, reference, or acknowledge the existence of other workspaces, companies, or data outside your scope
- NEVER reveal internal path structures (e.g., company names, workspace identifiers, storage organization)
- Treat the workspace as if it's the entire filesystem - it's the user's complete view
- If asked about other companies or workspaces, respond that you only have access to the current workspace data

When presenting file paths to users, use simple relative paths (e.g., "documents/report.pdf") without exposing internal storage structure.
"""

# Human approval required for write operations
WRITE_OPERATIONS_APPROVAL = {
    "write_file": True,
    "edit_file": True,
}

# Main agent tools
# Generate ls tool for direct access in main agent (also available in sub-agent)
_bucket_name = os.getenv("GCS_BUCKET_NAME")
if not _bucket_name:
    raise ValueError("GCS_BUCKET_NAME environment variable is required")

main_agent_tools = [
    gcs_ls_tool_generator(bucket_name=_bucket_name),
]

# Middleware configuration matching create_deep_agent
deepagent_middleware = [
    # MUST be first: Propagate config to state for sub-agents
    # (workaround for deepagents not propagating RunnableConfig)
    ConfigToStateMiddleware(),
    # Add mention context to prompt (after state is populated)
    MentionContextMiddleware(),
    TodoListMiddleware(),
    # EventTrackingMiddleware MUST be before SubAgentMiddleware
    # to intercept sub-agent calls and emit real-time events
    EventTrackingMiddleware(),
    SubAgentMiddleware(
        default_model=CLAUDE_HAIKU_4_5,
        default_tools=[],  # No default tools - tools are in sub-agents
        subagents=get_subagents(),  # Include all registered sub-agents
        default_middleware=[
            TodoListMiddleware(),
            SummarizationMiddleware(
                model=CLAUDE_HAIKU_4_5,
                max_tokens_before_summary=MAX_TOKENS_BEFORE_SUMMARY,
                messages_to_keep=MESSAGES_TO_KEEP,
            ),
            AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
            PatchToolCallsMiddleware(),
        ],
        default_interrupt_on=WRITE_OPERATIONS_APPROVAL,
        general_purpose_agent=True,
    ),
    SummarizationMiddleware(
        model=CLAUDE_HAIKU_4_5,
        max_tokens_before_summary=MAX_TOKENS_BEFORE_SUMMARY,
        messages_to_keep=MESSAGES_TO_KEEP,
    ),
    AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
    PatchToolCallsMiddleware(),
    HumanInTheLoopMiddleware(interrupt_on=WRITE_OPERATIONS_APPROVAL),
]

agent = create_agent(
    model=CLAUDE_SONNET_4_5,
    tools=main_agent_tools,
    middleware=deepagent_middleware,
    system_prompt=f"{RESEARCH_INSTRUCTIONS}\n\n{BASE_AGENT_PROMPT}",
    state_schema=MainAgentState,
).with_config({"recursion_limit": RECURSION_LIMIT})
