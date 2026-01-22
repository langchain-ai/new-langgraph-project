"""Agent nodes for 5STARS LangGraph.

Each node is a function that takes CaseState and returns state updates.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from agent.prompts import (
    DIALOG_AGENT_SYSTEM,
    DIALOG_AGENT_USER,
    ESCALATION_HANDLER_SYSTEM,
    ESCALATION_HANDLER_USER,
    MASTER_AGENT_SYSTEM,
    MASTER_AGENT_USER,
    MEMORY_AGENT_SYSTEM,
    MEMORY_AGENT_USER,
    REVIEW_AGENT_SYSTEM,
    REVIEW_AGENT_USER,
    format_prompt,
)
from agent.state import ActionItem, CaseStage, CaseState, ExecutionResult
from agent.tools import TOOLS_CATALOG

logger = logging.getLogger("5stars.nodes")


def _get_primary_llm() -> ChatGoogleGenerativeAI:
    """Get primary LLM for main actions."""
    return ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview",
        temperature=0.6,
        max_tokens=4096,
    )


def _get_secondary_llm() -> ChatGoogleGenerativeAI:
    """Get secondary LLM for validation/analysis."""
    return ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview",
        temperature=0.4,
        max_tokens=4096,
    )


def _extract_text_content(content: str | list) -> str:
    """Extract text from LLM response content.
    
    Args:
        content: LLM response content - can be string or list of content blocks
        
    Returns:
        Extracted text as string
    """
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
    return content


def _parse_json_response(response: str | list) -> dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code blocks.
    
    Args:
        response: LLM response content - can be string or list of content blocks
    """
    text = _extract_text_content(response).strip()
    # Remove markdown code blocks if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse JSON response: {text[:100]}...")
        return {}


# =============================================================================
# Master Agent Node
# =============================================================================


async def master_agent_node(state: CaseState) -> dict[str, Any]:
    """Master Agent - orchestrator that determines strategy and next stage.

    Analyzes the case and decides:
    - next_stage: which stage to move to
    - strategy: strategy for Dialog Agent
    - should_escalate: whether to escalate to manager
    """
    logger.info(f"Master Agent processing case {state.get('case_id')}")

    llm = _get_primary_llm()

    # Format dialog history
    dialog_history = state.get("dialog_history", [])
    dialog_str = "\n".join(
        [f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in dialog_history]
    ) or "Нет истории диалога"

    # Format memory context
    memory_context = state.get("relevant_history", "") or state.get("short_term_facts", "") or "Нет контекста"

    user_prompt = format_prompt(
        MASTER_AGENT_USER,
        case_id=state.get("case_id", "unknown"),
        current_stage=state.get("current_stage", CaseStage.RECEIVED),
        rating=state.get("rating", 0),
        review_text=state.get("review_text", ""),
        dialog_history=dialog_str,
        memory_context=memory_context,
    )

    messages = [
        SystemMessage(content=MASTER_AGENT_SYSTEM),
        HumanMessage(content=user_prompt),
    ]

    response = await llm.ainvoke(messages)
    result = _parse_json_response(response.content)

    # Determine next stage
    next_stage_str = result.get("next_stage", "analysis").upper()
    try:
        next_stage = CaseStage[next_stage_str]
    except KeyError:
        next_stage = CaseStage.ANALYSIS

    return {
        "next_stage": next_stage,
        "strategy": result.get("strategy", "empathy_first"),
        "should_escalate": result.get("should_escalate", False),
        "messages": [AIMessage(content=f"Master Agent decision: {result.get('reasoning', 'N/A')}")],
    }


# =============================================================================
# Memory Agent Node
# =============================================================================


async def memory_agent_node(state: CaseState) -> dict[str, Any]:
    """Memory Agent - manages context and retrieves relevant history.

    Tasks:
    - Extract facts from current dialog
    - Search for similar cases
    - Prepare context for other agents
    """
    logger.info(f"Memory Agent processing case {state.get('case_id')}")

    llm = _get_secondary_llm()

    # Format current dialog
    dialog_history = state.get("dialog_history", [])
    dialog_str = "\n".join(
        [f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in dialog_history]
    ) or "Нет истории"

    # Get last message
    messages_list = state.get("messages", [])
    last_message = messages_list[-1].content if messages_list else ""

    user_prompt = format_prompt(
        MEMORY_AGENT_USER,
        dialog_history=dialog_str,
        last_message=last_message,
        current_facts=state.get("short_term_facts", ""),
    )

    messages = [
        SystemMessage(content=MEMORY_AGENT_SYSTEM),
        HumanMessage(content=user_prompt),
    ]

    response = await llm.ainvoke(messages)
    result = _parse_json_response(response.content)

    # Format extracted facts
    facts = result.get("facts", [])
    facts_str = "\n".join([f"- {f.get('type', 'fact')}: {f.get('content', '')}" for f in facts])

    # TODO: Implement actual vector search for similar cases
    similar_cases = []

    return {
        "short_term_facts": facts_str or state.get("short_term_facts", ""),
        "relevant_history": result.get("context_summary", ""),
        "similar_cases": similar_cases,
    }


# =============================================================================
# Review Agent Node
# =============================================================================


async def review_agent_node(state: CaseState) -> dict[str, Any]:
    """Review Agent - analyzes reviews and extracts insights.

    Determines:
    - primary_issue: main problem
    - issue_severity: severity level
    - suggested_compensation: recommended compensation
    - sentiment: emotional tone
    """
    logger.info(f"Review Agent analyzing review for case {state.get('case_id')}")

    llm = _get_secondary_llm()

    # Get product and customer context
    product_ctx = state.get("product_context", {})
    customer_ctx = state.get("customer_context", {})

    user_prompt = format_prompt(
        REVIEW_AGENT_USER,
        rating=state.get("rating", 0),
        review_text=state.get("review_text", ""),
        pros=state.get("review_context", {}).get("pros", "Не указано"),
        cons=state.get("review_context", {}).get("cons", "Не указано"),
        product_category=product_ctx.get("category", "Неизвестно"),
        product_price=product_ctx.get("price", 0),
        total_orders=customer_ctx.get("total_orders", 0),
        total_reviews=customer_ctx.get("total_reviews", 0),
        average_rating=customer_ctx.get("average_rating", 0),
    )

    messages = [
        SystemMessage(content=REVIEW_AGENT_SYSTEM),
        HumanMessage(content=user_prompt),
    ]

    response = await llm.ainvoke(messages)
    result = _parse_json_response(response.content)

    return {
        "review_context": {
            "primary_issue": result.get("primary_issue", "other"),
            "issue_severity": result.get("issue_severity", "medium"),
            "sentiment": result.get("sentiment", "neutral"),
            "suggested_compensation": result.get("suggested_compensation", 0),
            "needs_manager": result.get("needs_manager", False),
            "key_facts": result.get("key_facts", []),
        },
    }


# =============================================================================
# Dialog Agent Node
# =============================================================================


async def dialog_agent_node(state: CaseState) -> dict[str, Any]:
    """Dialog Agent - generates personalized responses to customers.

    Uses strategy from Master Agent to craft appropriate message.
    """
    logger.info(f"Dialog Agent generating response for case {state.get('case_id')}")

    llm = _get_primary_llm()

    # Get review context
    review_ctx = state.get("review_context", {})

    # Format dialog history
    dialog_history = state.get("dialog_history", [])
    dialog_str = "\n".join(
        [f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in dialog_history]
    ) or "Первое сообщение"

    # Format similar dialogs
    similar = state.get("similar_cases", [])
    similar_str = "\n".join([f"- {c.get('resolution', 'N/A')}" for c in similar]) or "Нет данных"

    # Get customer context
    customer_ctx = state.get("customer_context", {})

    system_prompt = format_prompt(
        DIALOG_AGENT_SYSTEM,
        min_compensation=100,
        max_compensation=1000,
    )

    user_prompt = format_prompt(
        DIALOG_AGENT_USER,
        customer_name=customer_ctx.get("customer_name", "Уважаемый покупатель"),
        rating=state.get("rating", 0),
        primary_issue=review_ctx.get("primary_issue", "проблема с заказом"),
        strategy=state.get("strategy", "empathy_first"),
        review_text=state.get("review_text", ""),
        dialog_history=dialog_str,
        short_term_facts=state.get("short_term_facts", ""),
        similar_dialogs=similar_str,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    response = await llm.ainvoke(messages)
    ai_response = _extract_text_content(response.content).strip()

    # Prepare action to send message
    actions: list[ActionItem] = []
    if state.get("chat_id"):
        actions.append({
            "type": "send_wb_message",
            "params": {
                "chat_id": state.get("chat_id"),
                "message": ai_response,
            },
        })

    return {
        "ai_response": ai_response,
        "actions": actions,
        "messages": [AIMessage(content=ai_response)],
    }


# =============================================================================
# Action Executor Node
# =============================================================================


async def action_executor_node(state: CaseState) -> dict[str, Any]:
    """Action Executor - executes actions decided by other agents.

    Processes all pending actions and returns execution results.
    """
    actions = state.get("actions", [])
    logger.info(f"Action Executor processing {len(actions)} actions for case {state.get('case_id')}")

    execution_results: list[ExecutionResult] = []

    for action in actions:
        action_type = action.get("type", "")
        params = action.get("params", {})

        try:
            tool = TOOLS_CATALOG.get(action_type)
            if tool is None:
                raise ValueError(f"Unknown action type: {action_type}")

            # Execute the tool
            result = tool.invoke(params)

            execution_results.append({
                "status": "ok",
                "action": action,
                "result": result,
                "error": None,
            })
            logger.info(f"Action {action_type} executed successfully")

        except Exception as e:
            execution_results.append({
                "status": "error",
                "action": action,
                "result": None,
                "error": str(e),
            })
            logger.error(f"Action {action_type} failed: {e}")

    return {
        "execution_results": execution_results,
        "actions": [],  # Clear processed actions
    }


# =============================================================================
# Escalation Handler Node
# =============================================================================


async def escalation_handler_node(state: CaseState) -> dict[str, Any]:
    """Escalation Handler - prepares case for human manager.

    Generates summary and recommendations for manager.
    """
    logger.info(f"Escalation Handler processing case {state.get('case_id')}")

    llm = _get_secondary_llm()

    # Format dialog history
    dialog_history = state.get("dialog_history", [])
    dialog_str = "\n".join(
        [f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in dialog_history]
    ) or "Нет истории"

    # Format review analysis
    review_ctx = state.get("review_context", {})
    review_analysis = json.dumps(review_ctx, ensure_ascii=False, indent=2)

    user_prompt = format_prompt(
        ESCALATION_HANDLER_USER,
        case_id=state.get("case_id", "unknown"),
        rating=state.get("rating", 0),
        escalation_reason=state.get("strategy", "требуется внимание менеджера"),
        review_text=state.get("review_text", ""),
        dialog_history=dialog_str,
        review_analysis=review_analysis,
    )

    messages = [
        SystemMessage(content=ESCALATION_HANDLER_SYSTEM),
        HumanMessage(content=user_prompt),
    ]

    response = await llm.ainvoke(messages)
    result = _parse_json_response(response.content)

    # Prepare escalation actions
    actions: list[ActionItem] = [
        {
            "type": "escalate_to_manager",
            "params": {
                "case_id": state.get("case_id"),
                "reason": result.get("summary", "Требуется внимание менеджера"),
                "urgency": result.get("urgency", "normal"),
            },
        },
        {
            "type": "send_telegram_notification",
            "params": {
                "manager_id": 0,  # Will be assigned by escalate_to_manager
                "case_id": state.get("case_id"),
                "message": result.get("summary", "Новый кейс требует внимания"),
                "urgency": result.get("urgency", "normal"),
            },
        },
    ]

    return {
        "actions": actions,
        "is_managed_by_human": True,
        "current_stage": CaseStage.ESCALATION,
        "messages": [AIMessage(content=f"Escalated: {result.get('summary', 'N/A')}")],
    }


# =============================================================================
# Routing Functions
# =============================================================================


def route_after_master(state: CaseState) -> Literal["memory_agent", "escalation_handler", "__end__"]:
    """Route after Master Agent based on decisions."""
    if state.get("should_escalate"):
        return "escalation_handler"

    next_stage = state.get("next_stage")
    if next_stage in [CaseStage.RESOLVED, CaseStage.CLOSED]:
        return "__end__"

    return "memory_agent"


def route_after_memory(state: CaseState) -> Literal["review_agent", "dialog_agent", "__end__"]:
    """Route after Memory Agent based on current stage."""
    next_stage = state.get("next_stage")

    if next_stage == CaseStage.ANALYSIS:
        return "review_agent"
    elif next_stage in [CaseStage.COMPENSATION_OFFER, CaseStage.WAITING_RESPONSE]:
        return "dialog_agent"
    else:
        return "__end__"


def route_after_review(state: CaseState) -> Literal["dialog_agent", "escalation_handler", "__end__"]:
    """Route after Review Agent based on analysis."""
    review_ctx = state.get("review_context", {})

    if review_ctx.get("needs_manager"):
        return "escalation_handler"

    return "dialog_agent"


def route_after_dialog(state: CaseState) -> Literal["action_executor", "__end__"]:
    """Route after Dialog Agent."""
    actions = state.get("actions", [])
    if actions:
        return "action_executor"
    return "__end__"


def route_after_escalation(state: CaseState) -> Literal["action_executor", "__end__"]:
    """Route after Escalation Handler."""
    actions = state.get("actions", [])
    if actions:
        return "action_executor"
    return "__end__"
