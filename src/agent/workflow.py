"""Workflow for running a LangGraph ReAct agent with a weather tool and a chat model."""

import json
import logging
import os
import asyncio

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.agent.example_toolkit import ExampleToolkit

load_dotenv()

logging.basicConfig(level=logging.INFO)

# ========================= LLM
model = init_chat_model(model_provider="openai", model="gpt-4.1-mini", api_key=os.getenv("OPENAI_API_KEY"))


# ================================= NATIVE TOOLS
example_toolkit = ExampleToolkit.get_tools()

# ============================================ MCP TOOLS
client = MultiServerMCPClient(
    {
        "deepwiki": {
        "url": "https://mcp.deepwiki.com/mcp",
        "transport": "streamable_http"
        },
        "dnext_coder": {
        "url": "https://dnext-coder-mcp-server.pia-team.com/mcp/",
        "transport": "streamable_http",
        "headers": {
				"DS-API-KEY": os.getenv("DS_API_KEY")
			}
        }
    }
)

# Await the coroutine to get mcp_tools in a synchronous context
def get_mcp_tools_sync():
    return asyncio.run(client.get_tools())

mcp_tools = get_mcp_tools_sync()

# =========================== PROMPT
SYSTEM_PROMPT = "You are a helpful assistant that helps people find information."


# =========================== AGENT
workflow = create_react_agent(model=model, tools=example_toolkit+mcp_tools, prompt=SYSTEM_PROMPT)

# ====================== RUN
response = workflow.invoke({"messages": [{"role": "user", "content": "what is the weather in sf"}]})

logging.info(json.dumps(response, indent=2, default=str))
# logging.info(response["messages"][-1].content)