"""State definitions for 5STARS agent.

Simplified state with urgency classification and autonomous decision making.
All decisions are made by AI, with escalation tool for human involvement.
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
    HIGH = "high"          # 1-3★ или повторная жалоба
    NORMAL = "normal"      # 4★ или стандартная проблема
    LOW = "low"            # 5★ или простой вопрос


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



class CompletedAction(BaseModel):
    """Record of completed action."""
    
    action_type: ActionType
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

    # === Review Data ===
    review_text: str
    rating: int  # 1-5 stars
    pros: str  # Достоинства
    cons: str  # Недостатки
    
    # === Order Context ===
    product_name: str
    order_date: str

    # === Customer Context ===
    customer_name: str

    # === Dialog History (for multi-turn conversations) ===
    dialog_history: list[dict[str, str]]

    # === Agent Messages (LangGraph managed) ===
    messages: Annotated[list, add_messages]
    
    # === Case Analysis ===
    analysis: dict[str, Any]  # CaseAnalysis as dict

    # === Processing Status ===
    is_resolved: bool
    is_escalated: bool
    
    # === Results ===
    final_response: str
    actions_taken: list[dict[str, Any]]  # List of CompletedAction as dicts
    
    # === Error Handling ===
    error: Optional[str]
    retry_count: int  # Number of retries attempted
    
    # === Metrics (new) ===
    processing_started_at: str
    processing_completed_at: str


class AgentConfig(BaseModel):
    """Configuration for the 5STARS agent (configurable via LangSmith UI).
    
    These settings are passed at runtime through config["configurable"].
    Each field maps to an input in the LangSmith Assistant configuration panel.
    
    Field naming uses snake_case which LangSmith converts to "Title Case" in UI:
    - model_name → "Model Name"
    - temperature → "Temperature"  
    - max_tokens → "Max Tokens"
    - max_compensation → "Max Compensation"
    """

    # ==========================================================================
    # LLM Settings
    # ==========================================================================
    
    model_name: str = Field(
        default="gemini-3-flash-preview",
        description="AI model to use for agent reasoning",
        json_schema_extra={
            "langgraph_nodes": ["Analysis", "Agent"],
        },
    )
    temperature: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="LLM temperature (0.0-2.0). Higher values = more creative responses",
        json_schema_extra={
            "langgraph_nodes": ["Analysis", "Agent"],
        },
    )
    max_tokens: int = Field(
        default=2048,
        ge=256,
        le=8192,
        description="Maximum tokens in LLM response",
        json_schema_extra={
            "langgraph_nodes": ["Analysis", "Agent"],
        },
    )

    # ==========================================================================
    # Business Rules
    # ==========================================================================
    
    max_compensation: int = Field(
        default=1000,
        ge=0,
        le=10000,
        description="Maximum auto-approved compensation amount (₽)",
        json_schema_extra={
            "langgraph_nodes": ["Agent", "Analysis"],
        },
    )
    
    class Config:
        """Pydantic config for AgentConfig."""
        
        # Allow population by field name for compatibility
        populate_by_name = True
