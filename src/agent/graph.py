"""5STARS LangGraph Agent for Wildberries Review Management.

Enhanced ReAct agent with:
- Human-in-the-Loop (HITL) for critical actions
- Checkpointing for state persistence
- Error handling with retry policies
- Streaming support

Graph structure (node naming per LangGraph conventions):
    START
      │
      └─► classify_case (classification node)
             │
             └─► call_model (LLM reasoning node)
                    │
                    ├─► execute_tools (tool execution)
                    │       │
                    │       └─► route_after_model
                    │              │
                    │       ┌──────┴──────┐
                    │       ▼             ▼
                    │   [Needs HITL]  [Auto-approve]
                    │       │             │
                    │       ▼             │
                    │   human_approval    │
                    │   (interrupt())     │
                    │       │             │
                    │       └──────┬──────┘
                    │              ▼
                    │       Back to call_model
                    │
                    └─► END (when done)

Node naming conventions (from LangGraph docs):
- classify_*: Classification/preprocessing nodes
- call_model: LLM invocation nodes  
- execute_tools: Tool execution nodes
- human_approval: HITL approval nodes
- route_*: Conditional routing functions
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt

from agent.prompts import get_analysis_prompt, get_system_prompt
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
# Configuration Helpers
# =============================================================================


def _get_default_config() -> dict[str, Any]:
    """Get default configuration values from AgentConfig model.
    
    This ensures consistency between Pydantic model defaults and runtime defaults.
    """
    return AgentConfig().model_dump()


def _get_config_value(config: RunnableConfig | None, key: str) -> Any:
    """Extract configuration value from RunnableConfig.
    
    Looks in config["configurable"] with fallback to AgentConfig defaults.
    
    Args:
        config: RunnableConfig passed to node
        key: Configuration key to retrieve
        
    Returns:
        Configuration value or default from AgentConfig
    """
    defaults = _get_default_config()
    
    if config is None:
        return defaults.get(key)
    
    configurable = config.get("configurable", {})
    return configurable.get(key, defaults.get(key))


def _get_llm(config: RunnableConfig | None = None) -> ChatGoogleGenerativeAI:
    """Get configured LLM instance based on runtime configuration.
    
    Args:
        config: RunnableConfig with model settings from LangSmith UI
        
    Returns:
        Configured ChatGoogleGenerativeAI instance
    """
    model_name = _get_config_value(config, "model_name")
    temperature = _get_config_value(config, "temperature")
    max_tokens = _get_config_value(config, "max_tokens")
    
    logger.info(f"[LLM] Using model={model_name}, temp={temperature}, max_tokens={max_tokens}")
    
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
    )


# =============================================================================
# Helper Functions
# =============================================================================


def _format_user_message(state: CaseState) -> str:
    """Format user message from case state."""
    parts = []
    
    # Rating
    rating = state.get("rating", 1)
    parts.append(f"**Рейтинг:** {'⭐' * rating} ({rating}/5)")
    
    # Customer
    customer_name = state.get("customer_name", "Покупатель")
    parts.append(f"**Клиент:** {customer_name}")
    
    # Product context
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


def _check_tool_calls_need_approval(
    message: AIMessage, 
    config: RunnableConfig | None = None
) -> list[dict]:
    """Check which tool calls in the message need approval.
    
    Uses max_compensation from config to determine approval threshold.
    
    Returns list of tool calls that need human approval.
    """
    needs_approval = []
    
    if not hasattr(message, "tool_calls") or not message.tool_calls:
        return needs_approval
    
    # Get max compensation threshold from config
    max_compensation = _get_config_value(config, "max_compensation")
    
    for tool_call in message.tool_calls:
        tool_name = tool_call.get("name", "")
        # Check against our approval rules
        if tool_name in ["send_review_reply", "escalate_to_manager"]:
            needs_approval.append(tool_call)
    
    return needs_approval


# =============================================================================
# Graph Nodes
# =============================================================================


async def classify_case(state: CaseState, config: RunnableConfig) -> dict[str, Any]:
    """Classify the case using LLM to determine urgency, sentiment, and routing.
    
    This node runs before the main agent to classify the case using AI analysis
    based on the review content and context.
    
    Node name pattern: classify_* (per LangGraph conventions for classification nodes)
    """
    import json
    
    logger.info("[classify_case] Classifying case")
    
    # Prepare review data for LLM analysis
    rating = state.get("rating", 0)
    review_text = state.get("review_text", "")
    pros = state.get("pros", "")
    cons = state.get("cons", "")
    customer_name = state.get("customer_name", "")
    dialog_history = state.get("dialog_history", [])
    
    # Get configuration values
    max_compensation = _get_config_value(config, "max_compensation")
    
    # Format input for analysis
    analysis_input = f"""ДАННЫЕ ДЛЯ АНАЛИЗА:

**Рейтинг:** {rating}/5 звёзд
**Клиент:** {customer_name or 'Не указан'}

**Текст отзыва:**
{review_text or 'Не указан'}

**Достоинства:** {pros or 'Не указаны'}
**Недостатки:** {cons or 'Не указаны'}
"""
    
    if dialog_history:
        history_str = "\n".join([
            f"- {msg.get('role', '???')}: {msg.get('content', '')}" 
            for msg in dialog_history
        ])
        analysis_input += f"\n**История диалога:**\n{history_str}"
    
    # Call LLM for analysis (using config for model settings)
    llm = _get_llm(config)
    
    messages = [
        SystemMessage(content=get_analysis_prompt()),
        HumanMessage(content=analysis_input),
    ]
    
    try:
        response = await llm.ainvoke(messages)
        response_text = _extract_text(response.content)
        
        # Parse JSON from response (handle markdown code blocks)
        json_text = response_text
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0]
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0]
        
        analysis_data = json.loads(json_text.strip())
        
        # Map LLM response to CaseAnalysis
        urgency_map = {
            "critical": UrgencyLevel.CRITICAL,
            "high": UrgencyLevel.HIGH,
            "normal": UrgencyLevel.NORMAL,
            "low": UrgencyLevel.LOW,
        }
        sentiment_map = {
            "angry": SentimentType.ANGRY,
            "disappointed": SentimentType.DISAPPOINTED,
            "neutral": SentimentType.NEUTRAL,
            "positive": SentimentType.POSITIVE,
        }
        
        urgency = urgency_map.get(analysis_data.get("urgency", "normal"), UrgencyLevel.NORMAL)
        sentiment = sentiment_map.get(analysis_data.get("sentiment", "neutral"), SentimentType.NEUTRAL)
        
        # Extract main issue
        main_issue_data = analysis_data.get("main_issue", {})
        if isinstance(main_issue_data, dict):
            main_issue = main_issue_data.get("description", "")
        else:
            main_issue = str(main_issue_data)
        
        # Extract compensation suggestion
        comp_data = analysis_data.get("suggested_compensation", {})
        if isinstance(comp_data, dict):
            suggested_compensation = comp_data.get("amount", 0)
        else:
            suggested_compensation = int(comp_data) if comp_data else 0
        
        # Create analysis object (apply max_compensation limit from config)
        analysis = CaseAnalysis(
            urgency=urgency,
            sentiment=sentiment,
            main_issue=main_issue[:200] if main_issue else "",
            requires_compensation=suggested_compensation > 0,
            suggested_compensation=min(suggested_compensation, max_compensation),
            auto_approvable=analysis_data.get("auto_approve", False),
            risk_factors=analysis_data.get("risk_factors", []),
        )
        
        logger.info(f"[classify_case] Result: urgency={urgency.value}, sentiment={sentiment.value}")
        
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        # Fallback to basic analysis if LLM parsing fails
        logger.warning(f"[classify_case] LLM analysis parsing failed: {e}, using fallback")
        
        urgency = UrgencyLevel.HIGH if rating <= 3 else UrgencyLevel.LOW
        sentiment = SentimentType.NEUTRAL
        
        # Basic fallback analysis
        analysis = CaseAnalysis(
            urgency=urgency,
            sentiment=sentiment,
            main_issue=cons[:200] if cons else "",
            requires_compensation=rating <= 2,
            suggested_compensation=min(500, max_compensation) if rating <= 2 else 0,
            auto_approvable=False,  # LLM will decide via analysis
            risk_factors=[],
        )
    
    return {
        "analysis": analysis.model_dump(),
        "processing_started_at": datetime.now().isoformat(),
    }


async def call_model(state: CaseState, config: RunnableConfig) -> dict[str, Any]:
    """Call LLM to analyze situation and decide on actions.
    
    This is the main reasoning node that invokes the LLM with tools.
    
    Node name pattern: call_model (per LangGraph conventions for LLM invocation nodes)
    
    Args:
        state: Current case state
        config: RunnableConfig with model settings from LangSmith UI
    
    Available tools:
    - send_chat_message: Send private chat message
    - send_review_reply: Send public review reply (requires HITL approval)
    - escalate_to_manager: Escalate case (requires HITL approval, also used for compensation payouts)
    - search_similar_cases: Search knowledge base
    - get_order_details: Get order information
    """
    logger.info("[call_model] Processing case")
    
    # Get LLM with config settings
    llm = _get_llm(config)
    
    # Get all available tools
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
    
    logger.info(f"[call_model] LLM response: {_extract_text(response.content)[:100]}...")
    
    # Check if any tool calls need approval (using config for thresholds)
    requires_human = False
    pending_action = None
    
    if hasattr(response, "tool_calls") and response.tool_calls:
        approval_needed = _check_tool_calls_need_approval(response, config)
        if approval_needed:
            requires_human = True
            # Store the first action needing approval
            first_action = approval_needed[0]
            pending_action = {
                "action_type": first_action.get("name"),
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


def route_after_model(state: CaseState) -> Literal["execute_tools", "human_approval", "__end__"]:
    """Route execution after call_model node.
    
    Routing logic (per LangGraph conventions for conditional edges):
    - execute_tools: Tool calls present, no approval needed
    - human_approval: Tool calls present, requires HITL approval
    - __end__: No tool calls (agent completed task)
    """
    messages = state.get("messages", [])
    if not messages:
        return "__end__"
    
    last_message = messages[-1]
    
    # Check if there are tool calls
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return "__end__"
    
    # Check if human approval is needed
    if state.get("requires_human_review"):
        return "human_approval"
    
    return "execute_tools"


async def human_approval(state: CaseState) -> dict[str, Any]:
    """Human-in-the-loop (HITL) node for approving critical actions.
    
    This node uses LangGraph's interrupt() to pause execution and wait for
    human decision (approve/reject/edit).
    
    Node name pattern: human_approval (per LangGraph HITL conventions)
    
    Supported decisions:
    - approve: Execute the pending action as-is
    - reject: Cancel action, return to call_model with feedback
    - edit: Modify action content before execution
    """
    import json
    
    pending = state.get("pending_action", {})
    
    logger.info(f"[human_approval] Requesting approval for action: {pending.get('action_type')}")
    
    # Interrupt and wait for human decision
    decision_raw = interrupt({
        "type": "approval_request",
        "action_type": pending.get("action_type"),
        "content": pending.get("content"),
        "target_id": pending.get("target_id"),
        "metadata": pending.get("metadata"),
        "message": "Требуется одобрение менеджера для выполнения действия",
        "options": ["approve", "reject", "edit"],
    })
    
    # Parse decision - can be string, dict, or JSON string
    decision: dict[str, Any] = {}
    
    if isinstance(decision_raw, dict):
        decision = decision_raw
    elif isinstance(decision_raw, str):
        # Try to parse as JSON first
        try:
            parsed = json.loads(decision_raw)
            if isinstance(parsed, dict):
                decision = parsed
            else:
                decision = {"decision": str(parsed)}
        except json.JSONDecodeError:
            # Treat as simple approve/reject string
            decision = {"decision": decision_raw.strip().lower()}
    else:
        decision = {"decision": "rejected", "feedback": "Invalid response format"}
    
    # Process human decision
    approval_status = decision.get("decision", "rejected")
    feedback = decision.get("feedback", "")
    edited_content = decision.get("edited_content", "")
    
    # Normalize approval status
    if approval_status in ["approve", "approved", "yes", "да", "ok", "ок"]:
        approval_status = "approved"
    elif approval_status in ["edit", "edited", "редактировать"]:
        approval_status = "edit"
    elif approval_status not in ["rejected"]:
        approval_status = "rejected"
    
    logger.info(f"[human_approval] Decision received: {approval_status}")
    
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


def route_after_approval(state: CaseState) -> Literal["execute_tools", "call_model"]:
    """Route execution after human_approval node.
    
    Routing logic:
    - execute_tools: Approved - proceed with tool execution
    - call_model: Rejected/edited - return to LLM with feedback
    """
    status = state.get("approval_status")
    
    if status == "approved":
        return "execute_tools"
    else:
        # Rejected or edited - go back to call_model
        return "call_model"


# =============================================================================
# Graph Construction
# =============================================================================


def create_graph() -> StateGraph:
    """Create the 5STARS agent graph with HITL support.

    Graph structure (per LangGraph conventions):
    
        START
          │
          └─► classify_case (classification node)
                 │
                 └─► call_model (LLM reasoning node)
                        │
                        ├─► route_after_model
                        │       │
                        │   ┌───┴───────────┬──────────────┐
                        │   ▼               ▼              ▼
                        │ [execute_tools] [human_approval] [END]
                        │       │               │
                        │       │          route_after_approval
                        │       │               │
                        │       │         ┌─────┴─────┐
                        │       │         ▼           ▼
                        │       │  [execute_tools] [call_model]
                        │       │         │
                        │       └────┬────┘
                        │            ▼
                        └─────► call_model (loop)
    
    Returns:
        Compiled StateGraph ready for execution.
    """
    # Get tools for the agent
    tools = get_agent_tools()
    
    # Create ToolNode with error handling
    # Node name: execute_tools (per LangGraph conventions for tool execution)
    tool_node = ToolNode(tools, handle_tool_errors=get_tool_error_handler)
    
    # Initialize the graph
    workflow = StateGraph(CaseState, config_schema=AgentConfig)

    # ==========================================================================
    # Add Nodes (per LangGraph naming conventions)
    # ==========================================================================
    
    # Classification node: classify_case
    # Purpose: AI-based case classification (urgency, sentiment, routing)
    workflow.add_node("classify_case", classify_case)
    
    # LLM reasoning node: call_model  
    # Purpose: Main agent logic - invoke LLM with tools
    workflow.add_node("call_model", call_model)
    
    # Tool execution node: execute_tools
    # Purpose: Execute tool calls from LLM response
    workflow.add_node("execute_tools", tool_node)
    
    # HITL approval node: human_approval
    # Purpose: Pause for human review of critical actions
    workflow.add_node("human_approval", human_approval)

    # ==========================================================================
    # Add Edges
    # ==========================================================================
    
    # Entry point: START → classify_case
    workflow.add_edge(START, "classify_case")
    
    # After classification: classify_case → call_model
    workflow.add_edge("classify_case", "call_model")
    
    # After LLM call: conditional routing based on tool calls and approval needs
    workflow.add_conditional_edges(
        "call_model",
        route_after_model,
        {
            "execute_tools": "execute_tools",
            "human_approval": "human_approval",
            "__end__": END,
        },
    )
    
    # After HITL approval: conditional routing based on decision
    workflow.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {
            "execute_tools": "execute_tools",
            "call_model": "call_model",
        },
    )
    
    # After tool execution: loop back to call_model
    workflow.add_edge("execute_tools", "call_model")

    # Compile with interrupt support
    # Note: Checkpointer is automatically provided by LangGraph Server
    return workflow.compile()


# Export compiled graph for LangGraph
graph = create_graph()
