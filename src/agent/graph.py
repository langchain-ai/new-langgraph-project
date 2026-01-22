"""5STARS LangGraph Agent for Wildberries Review Management.

Single ReAct agent with tools for handling customer reviews.

Graph structure:
    START
      │
      └─► Agent (with tools)
             │
             ├─► Tool calls (if needed)
             │       │
             │       └─► Back to Agent
             │
             └─► END (when done)
"""

from __future__ import annotations

import logging
import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from agent.prompts import get_system_prompt
from agent.state import AgentConfig, CaseState
from agent.tools import get_agent_tools

logger = logging.getLogger("5stars.graph")


def _get_llm() -> ChatGoogleGenerativeAI:
    """Get configured LLM instance."""
    return ChatGoogleGenerativeAI(
        model=os.getenv("MODEL_NAME", "gemini-2.0-flash"),
        temperature=0.3,
        max_tokens=4096,
    )


def _format_user_message(state: CaseState) -> str:
    """Format user message from case state."""
    parts = []
    
    # Case info
    if state.get("case_id"):
        parts.append(f"**Case ID:** {state['case_id']}")
    if state.get("review_id"):
        parts.append(f"**Review ID:** {state['review_id']}")
    if state.get("chat_id"):
        parts.append(f"**Chat ID:** {state['chat_id']}")
    
    # Rating
    rating = state.get("rating", 0)
    parts.append(f"**Рейтинг:** {'⭐' * rating} ({rating}/5)")
    
    # Customer
    customer_name = state.get("customer_name", "Покупатель")
    parts.append(f"**Клиент:** {customer_name}")
    
    # Review content
    review_text = state.get("review_text", "")
    if review_text:
        parts.append(f"\n**Текст отзыва:**\n{review_text}")
    
    pros = state.get("pros", "")
    if pros:
        parts.append(f"\n**Достоинства:** {pros}")
    
    cons = state.get("cons", "")
    if cons:
        parts.append(f"\n**Недостатки:** {cons}")
    
    # Dialog history
    dialog_history = state.get("dialog_history", [])
    if dialog_history:
        history_str = "\n".join([
            f"- {msg.get('role', '???')}: {msg.get('content', '')}" 
            for msg in dialog_history
        ])
        parts.append(f"\n**История диалога:**\n{history_str}")
    
    parts.append("\n---\nПроанализируй ситуацию и выполни необходимые действия.")
    
    return "\n".join(parts)


async def agent_node(state: CaseState):
    """Main agent node - analyzes situation and decides on actions.
    
    Uses tools to:
    - Send chat messages
    - Send public review replies
    - Escalate to manager
    - Search similar cases
    """
    logger.info(f"Agent processing case {state.get('case_id')}")
    
    llm = _get_llm()
    tools = get_agent_tools()
    llm_with_tools = llm.bind_tools(tools)
    
    # Get existing messages or create initial
    messages = state.get("messages", [])
    
    if not messages:
        # First run - create initial messages
        from langchain_core.messages import HumanMessage, SystemMessage
        
        system_msg = SystemMessage(content=get_system_prompt())
        user_msg = HumanMessage(content=_format_user_message(state))
        messages = [system_msg, user_msg]
    
    # Invoke LLM
    response = await llm_with_tools.ainvoke(messages)
    
    logger.info(f"Agent response: {_extract_text(response.content)[:100]}...")
    
    return {"messages": [response]}


def _extract_text(content) -> str:
    """Extract text from LLM response content."""
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif hasattr(item, "text"):
                text_parts.append(item.text)
            elif isinstance(item, dict) and "text" in item:
                text_parts.append(item["text"])
        return "".join(text_parts)
    return str(content) if content else ""


def create_graph() -> StateGraph:
    """Create the 5STARS agent graph.

    Returns:
        Compiled StateGraph ready for execution.
    """
    # Get tools for the agent
    tools = get_agent_tools()
    
    # Initialize the graph
    workflow = StateGraph(CaseState, config_schema=AgentConfig)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))

    # Add edges
    workflow.add_edge(START, "agent")
    
    # After agent: either call tools or end
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "tools",
            END: END,
        },
    )
    
    # After tools: back to agent
    workflow.add_edge("tools", "agent")

    return workflow.compile()


# Export compiled graph for LangGraph
graph = create_graph()
