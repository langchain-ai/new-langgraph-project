"""State definitions for 5STARS agent.

Enhanced state with Human-in-the-Loop support, urgency classification,
and improved error handling.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, Optional

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


# =============================================================================
# Enums and Constants
# =============================================================================


class UrgencyLevel(str, Enum):
    """Urgency levels for case prioritization."""
    
    CRITICAL = "critical"  # 1★ + агрессия/юридические угрозы
    HIGH = "high"          # 1-2★ или повторная жалоба
    NORMAL = "normal"      # 3★ или стандартная проблема
    LOW = "low"            # 4-5★ или простой вопрос


class SentimentType(str, Enum):
    """Customer sentiment classification."""
    
    ANGRY = "angry"              # Злой, агрессивный
    DISAPPOINTED = "disappointed"  # Разочарованный
    NEUTRAL = "neutral"          # Нейтральный
    POSITIVE = "positive"        # Позитивный


class ActionType(str, Enum):
    """Types of actions that can be taken."""
    
    CHAT_MESSAGE = "chat_message"
    REVIEW_REPLY = "review_reply"
    ESCALATION = "escalation"
    COMPENSATION = "compensation"
    NO_ACTION = "no_action"


# =============================================================================
# Pydantic Models for Structured Data
# =============================================================================


class PendingAction(BaseModel):
    """Action pending human approval."""
    
    action_type: ActionType
    target_id: str = Field(description="ID чата или отзыва")
    content: str = Field(description="Текст сообщения/ответа")
    metadata: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(default="", description="Причина действия")


class CompletedAction(BaseModel):
    """Record of completed action."""
    
    action_type: ActionType
    target_id: str
    content: str
    status: Literal["success", "failed", "rejected"]
    timestamp: str = ""
    error: Optional[str] = None


class CaseAnalysis(BaseModel):
    """Results of initial case analysis."""
    
    urgency: UrgencyLevel = UrgencyLevel.NORMAL
    sentiment: SentimentType = SentimentType.NEUTRAL
    main_issue: str = Field(default="", description="Основная проблема")
    requires_compensation: bool = False
    suggested_compensation: int = Field(default=0, ge=0, le=5000)
    auto_approvable: bool = Field(
        default=False, 
        description="Можно ли автоматически одобрить ответ"
    )
    risk_factors: list[str] = Field(default_factory=list)


# =============================================================================
# Main State Definition
# =============================================================================


class CaseState(TypedDict, total=False):
    """State for 5STARS review handling agent.
    
    Contains all information about the current case being processed,
    with support for Human-in-the-Loop workflows.
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
    
    # === Order Context (new) ===
    order_id: str
    product_name: str
    product_sku: str
    order_date: str

    # === Customer Context ===
    customer_name: str
    customer_id: str
    customer_history: list[dict[str, Any]]  # Прошлые обращения клиента

    # === Dialog History (for multi-turn conversations) ===
    dialog_history: list[dict[str, str]]

    # === Agent Messages (LangGraph managed) ===
    messages: Annotated[list, add_messages]
    
    # === Case Analysis (new) ===
    analysis: dict[str, Any]  # CaseAnalysis as dict

    # === Human-in-the-Loop (new) ===
    pending_action: dict[str, Any]  # PendingAction as dict - awaiting approval
    approval_status: Literal["pending", "approved", "rejected", "edited"] | None
    approval_feedback: str  # Feedback from human reviewer
    edited_content: str  # Content edited by human

    # === Processing Status ===
    is_resolved: bool
    is_escalated: bool
    requires_human_review: bool  # Flag for HITL
    
    # === Results ===
    final_response: str
    actions_taken: list[dict[str, Any]]  # List of CompletedAction as dicts
    
    # === Error Handling ===
    error: Optional[str]
    retry_count: int  # Number of retries attempted
    
    # === Metrics (new) ===
    processing_started_at: str
    processing_completed_at: str


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
