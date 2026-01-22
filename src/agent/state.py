"""State definitions for 5STARS agent.

Simplified state for single-agent architecture with tools.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class CaseState(TypedDict, total=False):
    """State for 5STARS review handling agent.
    
    Contains all information about the current case being processed.
    """

    # === Case Identifiers ===
    case_id: str
    chat_id: str
    review_id: str

    # === Review Data ===
    review_text: str
    rating: int  # 1-5 stars
    pros: str  # Достоинства
    cons: str  # Недостатки

    # === Customer Context ===
    customer_name: str
    customer_id: str

    # === Dialog History (for multi-turn conversations) ===
    dialog_history: list[dict[str, str]]

    # === Agent Messages (LangGraph managed) ===
    messages: Annotated[list, add_messages]

    # === Processing Status ===
    is_resolved: bool
    is_escalated: bool
    
    # === Results ===
    final_response: str
    actions_taken: list[dict[str, Any]]
    
    # === Error Handling ===
    error: Optional[str]


class AgentConfig(TypedDict, total=False):
    """Configuration for the agent.
    
    Passed via configurable for runtime customization.
    """

    # Model settings
    model_name: str
    temperature: float
    max_tokens: int

    # Business rules
    max_compensation: int
    min_rating_for_auto: int
    
    # Feature flags
    enable_search: bool
    enable_escalation: bool
