"""5STARS LangGraph Agent for Wildberries Review Management.

Multi-agent system for automated customer review handling.
Architecture: Master → Memory → Review/Dialog → Action Executor

Graph structure:
    START
      │
      └─► Master Agent (Orchestrator)
             │
             ├─► Memory Agent (Context)
             │       │
             │       ├─► Review Agent (Analysis)
             │       │       │
             │       │       └─► Dialog Agent
             │       │               │
             │       │               └─► Action Executor → END
             │       │
             │       └─► Dialog Agent (Direct)
             │               │
             │               └─► Action Executor → END
             │
             └─► Escalation Handler (If needed)
                     │
                     └─► Action Executor → END
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    action_executor_node,
    dialog_agent_node,
    escalation_handler_node,
    master_agent_node,
    memory_agent_node,
    review_agent_node,
    route_after_dialog,
    route_after_escalation,
    route_after_master,
    route_after_memory,
    route_after_review,
)
from agent.state import AgentContext, CaseState

logger = logging.getLogger("5stars.graph")


def create_graph() -> StateGraph:
    """Create the 5STARS agent graph.

    Returns:
        Compiled StateGraph ready for execution.
    """
    # Initialize the graph with state and context schemas
    workflow = StateGraph(CaseState, config_schema=AgentContext)

    # ==========================================================================
    # Add Nodes
    # ==========================================================================

    # Master Agent - orchestrator that determines strategy
    workflow.add_node("master_agent", master_agent_node)

    # Memory Agent - manages context and history
    workflow.add_node("memory_agent", memory_agent_node)

    # Review Agent - analyzes reviews
    workflow.add_node("review_agent", review_agent_node)

    # Dialog Agent - generates customer responses
    workflow.add_node("dialog_agent", dialog_agent_node)

    # Action Executor - executes decided actions
    workflow.add_node("action_executor", action_executor_node)

    # Escalation Handler - prepares cases for managers
    workflow.add_node("escalation_handler", escalation_handler_node)

    # ==========================================================================
    # Add Edges
    # ==========================================================================

    # Entry point: START → Master Agent
    workflow.add_edge(START, "master_agent")

    # Master Agent → Memory Agent | Escalation Handler | END
    workflow.add_conditional_edges(
        "master_agent",
        route_after_master,
        {
            "memory_agent": "memory_agent",
            "escalation_handler": "escalation_handler",
            "__end__": END,
        },
    )

    # Memory Agent → Review Agent | Dialog Agent | END
    workflow.add_conditional_edges(
        "memory_agent",
        route_after_memory,
        {
            "review_agent": "review_agent",
            "dialog_agent": "dialog_agent",
            "__end__": END,
        },
    )

    # Review Agent → Dialog Agent | Escalation Handler | END
    workflow.add_conditional_edges(
        "review_agent",
        route_after_review,
        {
            "dialog_agent": "dialog_agent",
            "escalation_handler": "escalation_handler",
            "__end__": END,
        },
    )

    # Dialog Agent → Action Executor | END
    workflow.add_conditional_edges(
        "dialog_agent",
        route_after_dialog,
        {
            "action_executor": "action_executor",
            "__end__": END,
        },
    )

    # Escalation Handler → Action Executor | END
    workflow.add_conditional_edges(
        "escalation_handler",
        route_after_escalation,
        {
            "action_executor": "action_executor",
            "__end__": END,
        },
    )

    # Action Executor → END
    workflow.add_edge("action_executor", END)

    return workflow


# Create and compile the graph
workflow = create_graph()
graph = workflow.compile(name="5STARS Agent")


# =============================================================================
# Convenience Functions
# =============================================================================


async def process_case(
    case_id: int,
    review_text: str,
    rating: int,
    chat_id: str | None = None,
    customer_name: str | None = None,
    **kwargs: Any,
) -> CaseState:
    """Process a case through the agent graph.

    Args:
        case_id: Unique case identifier
        review_text: Text of the review
        rating: Star rating (1-5)
        chat_id: Optional Wildberries chat ID
        customer_name: Optional customer name
        **kwargs: Additional state fields

    Returns:
        Final CaseState after processing
    """
    from agent.state import CaseStage

    initial_state: CaseState = {
        "case_id": case_id,
        "review_text": review_text,
        "rating": rating,
        "chat_id": chat_id or "",
        "current_stage": CaseStage.RECEIVED,
        "messages": [],
        "dialog_history": [],
        "actions": [],
        "execution_results": [],
        "is_managed_by_human": False,
        "retry_count": 0,
        **kwargs,
    }

    if customer_name:
        initial_state["customer_context"] = {"customer_name": customer_name}

    logger.info(f"Processing case {case_id} with rating {rating}⭐")

    result = await graph.ainvoke(initial_state)

    logger.info(f"Case {case_id} processed. Final stage: {result.get('current_stage')}")

    return result


async def process_message(
    case_id: int,
    message: str,
    current_state: CaseState,
) -> CaseState:
    """Process a new customer message for an existing case.

    Args:
        case_id: Case identifier
        message: New message from customer
        current_state: Current case state

    Returns:
        Updated CaseState after processing
    """
    from langchain_core.messages import HumanMessage

    # Add new message to state
    updated_state = {
        **current_state,
        "messages": current_state.get("messages", []) + [HumanMessage(content=message)],
    }

    # Update dialog history
    dialog_history = current_state.get("dialog_history", [])
    dialog_history.append({"role": "customer", "content": message})
    updated_state["dialog_history"] = dialog_history

    logger.info(f"Processing new message for case {case_id}")

    result = await graph.ainvoke(updated_state)

    return result
