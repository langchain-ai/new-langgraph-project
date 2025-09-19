"""Workflow for running a LangGraph ReAct agent with a weather tool and a chat model."""

import json
import logging
import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama

from src.ai.toolkits.example_toolkit import ExampleToolkit
from src.ai.toolkits.dpc_toolkit import DPCToolkit
from src.ai.mcp.mcp_client import get_mcp_tools_optional
from src.ai.prompts.stc_prompt import STC_PROMPT

load_dotenv()

logging.basicConfig(level=logging.INFO)

# ==================== LLM =====================
# model = init_chat_model(model_provider="openai", model=os.getenv("MODEL_NAME"), api_key=os.getenv("OPENAI_API_KEY"))

model = ChatOllama(
    model=os.getenv("MODEL_NAME"),
    validate_model_on_init=True,
    temperature=1.0,
    seed=42,
    reasoning=False,
    num_ctx=32000,
    max_tokens=4096,
    base_url="http://localhost:11434",
    # other params ...
)

# ==================== TOOLS ====================
dpc_toolkit = DPCToolkit.get_tools()

# example_toolkit = ExampleToolkit.get_tools()
# mcp_tools = get_mcp_tools_optional()

tools = dpc_toolkit

# ===================== CREATE AGENT ===========================
stc_agent = create_react_agent(model=model, tools=tools, prompt=STC_PROMPT)


# ====================== RUN
# response = stc_agent.invoke({"messages": [{"role": "user", "content": "what is the weather in sf"}]})

# logging.info(json.dumps(response, indent=2, default=str))
# logging.info(response["messages"][-1].content)
