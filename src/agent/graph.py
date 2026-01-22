"""5STARS LangGraph Agent for Wildberries Review Management.

Enhanced ReAct agent with:
- Human-in-the-Loop (HITL) for critical actions
- Checkpointing for state persistence
- Error handling with retry policies
- Streaming support

Graph structure:
    START
      │
      └─► Analyze Case
             │
             └─► Agent (with tools)
                    │
                    ├─► Tool calls
                    │       │
                    │       └─► Check Approval
                    │              │
                    │       ┌──────┴──────┐
                    │       ▼             ▼
                    │   [Needs HITL]  [Auto-approve]
                    │       │             │
                    │       ▼             │
                    │   interrupt()       │
                    │       │             │
                    │       └──────┬──────┘
                    │              ▼
                    │       Back to Agent
                    │
                    └─► END (when done)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt

from agent.prompts import get_system_prompt
from agent.state import (
    ActionType,
    AgentConfig,
    CaseAnalysis,
    CaseState,
    SentimentType,
    UrgencyLevel,
)
from agent.tools import (
    get_agent_tools,
    get_tool_error_handler,
    tool_requires_approval,
)

logger = logging.getLogger("5stars.graph")


# =============================================================================
# Configuration
# =============================================================================


def _get_llm() -> ChatGoogleGenerativeAI:
    """Get configured LLM instance."""
    return ChatGoogleGenerativeAI(
        model=os.getenv("MODEL_NAME", "gemini-3-flash-preview"),
        temperature=1,
        max_tokens=2048,
    )


# =============================================================================
# Helper Functions
# =============================================================================


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
    rating = state.get("rating", 1)
    parts.append(f"**Рейтинг:** {'⭐' * rating} ({rating}/5)")
    
    # Customer
    customer_name = state.get("customer_name", "Покупатель")
    parts.append(f"**Клиент:** {customer_name}")
    
    # Order context (new)
    if state.get("order_id"):
        parts.append(f"**Заказ:** {state['order_id']}")
    if state.get("product_name"):
        parts.append(f"**Товар:** {state['product_name']}")
    
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
    
    # Analysis results (if available)
    analysis = state.get("analysis")
    if analysis:
        parts.append(f"\n**Анализ:**")
        parts.append(f"- Срочность: {analysis.get('urgency', 'normal')}")
        parts.append(f"- Тональность: {analysis.get('sentiment', 'neutral')}")
        if analysis.get("main_issue"):
            parts.append(f"- Проблема: {analysis['main_issue']}")
        if analysis.get("risk_factors"):
            parts.append(f"- Риски: {', '.join(analysis['risk_factors'])}")
    
    parts.append("\n---\nПроанализируй ситуацию и выполни необходимые действия.")
    
    return "\n".join(parts)


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


def _check_tool_calls_need_approval(message: AIMessage) -> list[dict]:
    """Check which tool calls in the message need approval.
    
    Returns list of tool calls that need human approval.
    """
    needs_approval = []
    
    if not hasattr(message, "tool_calls") or not message.tool_calls:
        return needs_approval
    
    for tool_call in message.tool_calls:
        tool_name = tool_call.get("name", "")
        # Check against our approval rules
        if tool_name in ["send_review_reply", "escalate_to_manager"]:
            needs_approval.append(tool_call)
        elif tool_name == "offer_compensation":
            # Check amount for conditional approval
            args = tool_call.get("args", {})
            if args.get("amount", 0) > 500:
                needs_approval.append(tool_call)
    
    return needs_approval


# =============================================================================
# Graph Nodes
# =============================================================================


async def analyze_case_node(state: CaseState) -> dict[str, Any]:
    """Analyze the case and determine urgency, sentiment, and routing.
    
    This node runs before the main agent to classify the case.
    """
    logger.info(f"Analyzing case {state.get('case_id')}")
    
    rating = state.get("rating", 3)
    review_text = state.get("review_text", "").lower()
    cons = state.get("cons", "").lower()
    
    # Determine urgency based on rating and keywords
    urgency = UrgencyLevel.NORMAL
    sentiment = SentimentType.NEUTRAL
    risk_factors = []
    
    # Rating-based urgency
    if rating <= 1:
        urgency = UrgencyLevel.HIGH
    elif rating <= 2:
        urgency = UrgencyLevel.NORMAL
    elif rating >= 4:
        urgency = UrgencyLevel.LOW
    
    # Keyword-based sentiment and risk analysis
    angry_keywords = ["ужас", "кошмар", "обман", "мошенник", "суд", "прокуратур", 
                      "роспотребнадзор", "жалоб", "верните деньги", "никогда больше"]
    disappointed_keywords = ["разочарован", "ожидал", "к сожалению", "не рекомендую"]
    positive_keywords = ["спасибо", "отлично", "рекомендую", "доволен", "супер"]
    
    combined_text = f"{review_text} {cons}"
    
    for keyword in angry_keywords:
        if keyword in combined_text:
            sentiment = SentimentType.ANGRY
            urgency = UrgencyLevel.CRITICAL if rating <= 2 else UrgencyLevel.HIGH
            risk_factors.append(f"Обнаружено: '{keyword}'")
            break
    
    if sentiment == SentimentType.NEUTRAL:
        for keyword in disappointed_keywords:
            if keyword in combined_text:
                sentiment = SentimentType.DISAPPOINTED
                break
        
        for keyword in positive_keywords:
            if keyword in combined_text:
                sentiment = SentimentType.POSITIVE
                break
    
    # Legal risk detection
    legal_keywords = ["суд", "адвокат", "юрист", "прокуратур", "роспотребнадзор"]
    for keyword in legal_keywords:
        if keyword in combined_text:
            risk_factors.append("Юридические риски")
            urgency = UrgencyLevel.CRITICAL
            break
    
    # Determine if auto-approvable (only positive reviews with 4-5 stars)
    auto_approvable = rating >= 4 and sentiment in [SentimentType.POSITIVE, SentimentType.NEUTRAL]
    
    # Create analysis
    analysis = CaseAnalysis(
        urgency=urgency,
        sentiment=sentiment,
        main_issue=cons[:200] if cons else "",
        requires_compensation=rating <= 2,
        suggested_compensation=500 if rating <= 2 else (200 if rating == 3 else 0),
        auto_approvable=auto_approvable,
        risk_factors=risk_factors,
    )
    
    logger.info(f"Case analysis: urgency={urgency.value}, sentiment={sentiment.value}")
    
    return {
        "analysis": analysis.model_dump(),
        "processing_started_at": datetime.now().isoformat(),
    }


async def agent_node(state: CaseState) -> dict[str, Any]:
    """Main agent node - analyzes situation and decides on actions.
    
    Uses tools to:
    - Send chat messages
    - Send public review replies (requires approval)
    - Escalate to manager (requires approval)
    - Search similar cases
    - Offer compensation
    """
    logger.info(f"Agent processing case {state.get('case_id')}")
    
    llm = _get_llm()
    tools = get_agent_tools()
    llm_with_tools = llm.bind_tools(tools)
    
    # Get existing messages from state
    state_messages = list(state.get("messages", []))
    
    if not state_messages:
        # First run - create initial user message
        user_msg = HumanMessage(content=_format_user_message(state))
        state_messages = [user_msg]
        messages_to_save = [user_msg]
    else:
        messages_to_save = []
    
    # Always prepend SystemMessage for each LLM call
    system_msg = SystemMessage(content=get_system_prompt())
    messages_for_llm = [system_msg] + state_messages
    
    # Invoke LLM
    response = await llm_with_tools.ainvoke(messages_for_llm)
    
    logger.info(f"Agent response: {_extract_text(response.content)[:100]}...")
    
    # Check if any tool calls need approval
    requires_human = False
    pending_action = None
    
    if hasattr(response, "tool_calls") and response.tool_calls:
        approval_needed = _check_tool_calls_need_approval(response)
        if approval_needed:
            requires_human = True
            # Store the first action needing approval
            first_action = approval_needed[0]
            pending_action = {
                "action_type": first_action.get("name"),
                "target_id": first_action.get("args", {}).get("review_id") or 
                            first_action.get("args", {}).get("chat_id") or
                            first_action.get("args", {}).get("case_id", ""),
                "content": first_action.get("args", {}).get("reply_text") or
                          first_action.get("args", {}).get("message") or
                          first_action.get("args", {}).get("reason", ""),
                "metadata": first_action.get("args", {}),
                "tool_call_id": first_action.get("id"),
            }
    
    return {
        "messages": messages_to_save + [response],
        "requires_human_review": requires_human,
        "pending_action": pending_action,
    }


def should_continue(state: CaseState) -> Literal["tools", "human_review", "__end__"]:
    """Determine the next step after agent node.
    
    Routes to:
    - tools: if there are tool calls that don't need approval
    - human_review: if there are tool calls that need approval
    - __end__: if no tool calls (agent is done)
    """
    messages = state.get("messages", [])
    if not messages:
        return "__end__"
    
    last_message = messages[-1]
    
    # Check if there are tool calls
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return "__end__"
    
    # Check if human review is needed
    if state.get("requires_human_review"):
        return "human_review"
    
    return "tools"


async def human_review_node(state: CaseState) -> dict[str, Any]:
    """Human-in-the-loop node for approving critical actions.
    
    This node interrupts execution and waits for human decision.
    """
    pending = state.get("pending_action", {})
    
    logger.info(f"HITL: Requesting approval for {pending.get('action_type')}")
    
    # Interrupt and wait for human decision
    decision = interrupt({
        "type": "approval_request",
        "action_type": pending.get("action_type"),
        "content": pending.get("content"),
        "target_id": pending.get("target_id"),
        "metadata": pending.get("metadata"),
        "message": "Требуется одобрение менеджера для выполнения действия",
        "options": ["approve", "reject", "edit"],
    })
    
    # Process human decision
    approval_status = decision.get("decision", "rejected")
    feedback = decision.get("feedback", "")
    edited_content = decision.get("edited_content", "")
    
    logger.info(f"HITL: Decision received - {approval_status}")
    
    messages = list(state.get("messages", []))
    last_message = messages[-1] if messages else None
    
    if approval_status == "rejected":
        # Create a tool message indicating rejection
        if last_message and hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_call_id = pending.get("tool_call_id") or last_message.tool_calls[0].get("id")
            rejection_msg = ToolMessage(
                content=f"❌ Действие отклонено менеджером. Причина: {feedback or 'не указана'}. "
                        "Попробуй другой подход.",
                tool_call_id=tool_call_id,
            )
            return {
                "messages": [rejection_msg],
                "approval_status": "rejected",
                "approval_feedback": feedback,
                "requires_human_review": False,
                "pending_action": None,
            }
    
    elif approval_status == "edit":
        # Manager edited the content - update and proceed
        if last_message and hasattr(last_message, "tool_calls") and last_message.tool_calls:
            tool_call_id = pending.get("tool_call_id") or last_message.tool_calls[0].get("id")
            edit_msg = ToolMessage(
                content=f"✏️ Контент изменён менеджером. Используй новую версию: {edited_content}",
                tool_call_id=tool_call_id,
            )
            return {
                "messages": [edit_msg],
                "approval_status": "edited",
                "edited_content": edited_content,
                "approval_feedback": feedback,
                "requires_human_review": False,
                "pending_action": None,
            }
    
    # Approved - continue with original action
    return {
        "approval_status": "approved",
        "approval_feedback": feedback,
        "requires_human_review": False,
    }


def after_human_review(state: CaseState) -> Literal["tools", "agent"]:
    """Route after human review based on decision."""
    status = state.get("approval_status")
    
    if status == "approved":
        return "tools"
    else:
        # Rejected or edited - go back to agent
        return "agent"


# =============================================================================
# Graph Construction
# =============================================================================


def create_graph() -> StateGraph:
    """Create the 5STARS agent graph with HITL support.

    Returns:
        Compiled StateGraph ready for execution.
    """
    # Get tools for the agent
    tools = get_agent_tools()
    
    # Create ToolNode with error handling
    tool_node = ToolNode(tools, handle_tool_errors=get_tool_error_handler)
    
    # Initialize the graph
    workflow = StateGraph(CaseState, config_schema=AgentConfig)

    # Add nodes
    workflow.add_node("analyze", analyze_case_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("human_review", human_review_node)

    # Add edges
    workflow.add_edge(START, "analyze")
    workflow.add_edge("analyze", "agent")
    
    # After agent: route based on tool calls and approval needs
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "human_review": "human_review",
            "__end__": END,
        },
    )
    
    # After human review: route based on decision
    workflow.add_conditional_edges(
        "human_review",
        after_human_review,
        {
            "tools": "tools",
            "agent": "agent",
        },
    )
    
    # After tools: back to agent
    workflow.add_edge("tools", "agent")

    # Compile with interrupt support
    # Note: Checkpointer is automatically provided by LangGraph Server
    return workflow.compile()


# Export compiled graph for LangGraph
graph = create_graph()
