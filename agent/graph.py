"""5STARS LangGraph Agent for Wildberries Review Management.

ReAct agent with:
- Autonomous decision making (AI decides all actions)
- Tool for human handoff when needed
- Checkpointing for state persistence
- Error handling with retry policies
- Streaming support
- Analysis-first architecture (анализ перед каждым выполнением)

Graph structure:
    START
      │
      └─► Analysis (Анализ ситуации)
             │
             └─► Agent (Основной агент с инструментами)
                    │
                    ├─► Tools (Выполнение действий)
                    │     │
                    │     └─► Agent (loop)
                    │
                    └─► END (завершение)

Node naming:
- Analysis: Анализ контекста и ситуации (AI размышления)
- Agent: Основной агент выполняющий действия (AI actions)
- Tools: Tool execution node

Data flow:
- При каждом запуске графа Analysis перепроверяет ситуацию
- Analysis помнит о предыдущих анализах и информации кейса
- Agent получает результаты анализа и базовую информацию о кейсе в промпте
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
from langgraph.types import Command

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
    """Format user message from case state with analysis results."""
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
    
    # Analysis results (ALWAYS available from Analysis node)
    analysis = state.get("analysis")
    if analysis:
        parts.append(f"\n**=== РЕЗУЛЬТАТЫ АНАЛИЗА (от агента-аналитика) ===**")
        parts.append(f"- **Срочность:** {analysis.get('urgency', 'normal')}")
        parts.append(f"- **Тональность:** {analysis.get('sentiment', 'neutral')}")
        if analysis.get("main_issue"):
            parts.append(f"- **Проблема:** {analysis['main_issue']}")
        if analysis.get("risk_factors"):
            parts.append(f"- **Риски:** {', '.join(analysis['risk_factors'])}")
        if analysis.get("requires_compensation"):
            compensation = analysis.get("suggested_compensation", 0)
            if compensation > 0:
                parts.append(f"- **Рекомендуемая компенсация:** {compensation}₽")
    
    parts.append("\n---\nВыполни необходимые действия на основе анализа.")
    
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





# =============================================================================
# Graph Nodes
# =============================================================================


async def analysis_node(state: CaseState, config: RunnableConfig) -> dict[str, Any]:
    """Analyze the case using LLM to determine urgency, sentiment, and routing.
    
    ВСЕГДА ПЕРВАЯ НОДА в графе. При каждом запуске графа (новый триггер)
    агент анализа перепроверяет ситуацию, помня о предыдущих анализах
    и всей информации кейса из state.
    
    Этот узел отвечает за размышления - что было и что нужно сделать.
    """
    import json
    
    logger.info("[Analysis] Analyzing case")
    
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
        
        logger.info(f"[Analysis] Result: urgency={urgency.value}, sentiment={sentiment.value}")
        
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        # Fallback to basic analysis if LLM parsing fails
        logger.warning(f"[Analysis] LLM analysis parsing failed: {e}, using fallback")
        
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


async def agent_node(state: CaseState, config: RunnableConfig) -> dict[str, Any]:
    """Main agent node - invoke LLM with tools to execute actions.
    
    Основной агент выполняющий действия. Вызывается после Analysis node,
    который уже провёл анализ ситуации.
    
    Available tools:
    - send_chat_message: Send private chat message
    - send_review_reply: Send public review reply
    - call_the_manager: Hand off case to human manager
    - search_similar_cases: Search knowledge base
    
    ВАЖНО: Базовая информация о кейсе и результаты анализа передаются
    в промпте через _format_user_message(), поэтому инструмент get_case_details
    больше не нужен.
    """
    logger.info("[Agent] Processing case")
    
    # Get LLM with config settings
    llm = _get_llm(config)
    
    # Get all available tools
    tools = get_agent_tools()
    llm_with_tools = llm.bind_tools(tools)
    
    # Get existing messages from state
    state_messages = list(state.get("messages", []))
    
    if not state_messages:
        # First run - create initial user message with case info and analysis
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
    
    logger.info(f"[Agent] LLM response: {_extract_text(response.content)[:100]}...")
    
    return {
        "messages": messages_to_save + [response],
    }


def route_after_agent(state: CaseState) -> Literal["Tools", "__end__"]:
    """Route execution after Agent node.
    
    Simple routing:
    - Tools: Tool calls present - execute them
    - __end__: No tool calls (agent completed task)
    """
    messages = state.get("messages", [])
    if not messages:
        return "__end__"
    
    last_message = messages[-1]
    
    # Check if there are tool calls
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return "__end__"
    
    return "Tools"





# =============================================================================
# Graph Construction
# =============================================================================


def create_graph() -> StateGraph:
    """Create the 5STARS agent graph.

    Graph structure:
    
        START
          │
          └─► Analysis (Анализ ситуации - размышления)
                 │
                 └─► Agent (Основной агент - действия)
                        │
                        ├─► Tools (Выполнение инструментов)
                        │     │
                        │     └─► Agent (loop)
                        │
                        └─► END (завершение)
    
    Workflow:
    1. При каждом запуске графа (триггер) сначала Analysis
    2. Analysis анализирует ситуацию помня о предыдущих анализах
    3. Agent получает результаты анализа и выполняет действия
    4. Tools выполняют действия (сообщения, эскалация и т.д.)
    5. Возврат к Agent для следующего цикла или завершение
    
    Returns:
        Compiled StateGraph ready for execution.
    """
    # Get tools for the agent
    tools = get_agent_tools()
    
    # Create ToolNode with error handling
    tool_node = ToolNode(tools, handle_tool_errors=get_tool_error_handler)
    
    # Initialize the graph
    workflow = StateGraph(CaseState, config_schema=AgentConfig)

    # ==========================================================================
    # Add Nodes
    # ==========================================================================
    
    # Analysis node: ПЕРВАЯ нода - анализ ситуации (размышления)
    workflow.add_node("Analysis", analysis_node)
    
    # Agent node: основной агент выполняющий действия
    workflow.add_node("Agent", agent_node)
    
    # Tools node: execute tool calls from Agent
    workflow.add_node("Tools", tool_node)

    # ==========================================================================
    # Add Edges
    # ==========================================================================
    
    # Entry point: START → Analysis (всегда начинаем с анализа)
    workflow.add_edge(START, "Analysis")
    
    # After Analysis: всегда переходим к Agent
    workflow.add_edge("Analysis", "Agent")
    
    # After Agent: conditional routing
    workflow.add_conditional_edges(
        "Agent",
        route_after_agent,
        {
            "Tools": "Tools",
            "__end__": END,
        },
    )
    
    # After Tools: всегда возврат к Agent (loop)
    workflow.add_edge("Tools", "Agent")

    # Compile
    return workflow.compile()


# Export compiled graph for LangGraph
graph = create_graph()
