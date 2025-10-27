from langchain.agents import create_agent
from langchain.agents.middleware import (
    HumanInTheLoopMiddleware,
    TodoListMiddleware,
)
from langchain.agents.middleware.summarization import SummarizationMiddleware
from langchain_anthropic.middleware import AnthropicPromptCachingMiddleware
from deepagents import SubAgentMiddleware
from deepagents.middleware.patch_tool_calls import PatchToolCallsMiddleware

from agent.gcs_middleware import GCSFilesystemMiddleware

# Model Configuration
MODEL_NAME = "claude-sonnet-4-20250514"
MAX_TOKENS_BEFORE_SUMMARY = 170000
MESSAGES_TO_KEEP = 6
RECURSION_LIMIT = 1000

# Prompts
BASE_AGENT_PROMPT = "In order to complete the objective that the user asks of you, you have access to a number of standard tools."
RESEARCH_INSTRUCTIONS = """
You are an expert financial advisor for a company data. You take company problems and deliver clear answers.
"""

# GCS middleware (reads GCS_BUCKET_NAME and GOOGLE_CLOUD_CREDENTIALS_JSON from env)
gcs_middleware = GCSFilesystemMiddleware()

# Human approval required for write operations
WRITE_OPERATIONS_APPROVAL = {
    "write_file": True,
    "edit_file": True,
}

# Middleware configuration matching create_deep_agent
deepagent_middleware = [
    TodoListMiddleware(),
    gcs_middleware,
    SubAgentMiddleware(
        default_model=MODEL_NAME,
        default_tools=gcs_middleware.tools,
        subagents=[],
        default_middleware=[
            TodoListMiddleware(),
            gcs_middleware,
            SummarizationMiddleware(
                model=MODEL_NAME,
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
        model=MODEL_NAME,
        max_tokens_before_summary=MAX_TOKENS_BEFORE_SUMMARY,
        messages_to_keep=MESSAGES_TO_KEEP,
    ),
    AnthropicPromptCachingMiddleware(unsupported_model_behavior="ignore"),
    PatchToolCallsMiddleware(),
    HumanInTheLoopMiddleware(interrupt_on=WRITE_OPERATIONS_APPROVAL),
]

graph = create_agent(
    model=MODEL_NAME,
    tools=gcs_middleware.tools,
    middleware=deepagent_middleware,
    system_prompt=f"{RESEARCH_INSTRUCTIONS}\n\n{BASE_AGENT_PROMPT}",
).with_config({"recursion_limit": RECURSION_LIMIT})
