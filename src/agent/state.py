"""State definitions for 5STARS agent.

Defines CaseState - the central state object passed between all nodes in the graph.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class CaseStage(str, Enum):
    """Stages of case processing."""

    RECEIVED = "received"
    ANALYSIS = "analysis"
    COMPENSATION_OFFER = "compensation_offer"
    WAITING_RESPONSE = "waiting_response"
    WAITING_FIX = "waiting_fix"
    ESCALATION = "escalation"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IssueSeverity(str, Enum):
    """Severity levels for issues."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewAnalysis(TypedDict, total=False):
    """Analysis result from Review Agent."""

    primary_issue: str
    issue_severity: IssueSeverity
    sentiment: str
    suggested_compensation: int
    needs_manager: bool
    key_facts: list[str]


class ProductContext(TypedDict, total=False):
    """Product information context."""

    product_id: str
    product_name: str
    category: str
    price: float
    seller_id: str


class CustomerContext(TypedDict, total=False):
    """Customer information context."""

    customer_id: str
    customer_name: str
    total_orders: int
    total_reviews: int
    average_rating: float


class ActionItem(TypedDict):
    """Action to be executed."""

    type: str
    params: dict[str, Any]


class ExecutionResult(TypedDict):
    """Result of action execution."""

    status: str
    action: ActionItem
    result: Optional[dict[str, Any]]
    error: Optional[str]


class CaseState(TypedDict, total=False):
    """Central state for case processing in 5STARS.

    This state is passed between all nodes in the graph.
    Uses Annotated types for automatic message handling.
    """

    # === Identifiers ===
    case_id: int
    chat_id: str
    review_id: str

    # === Messages (with auto-append via add_messages) ===
    messages: Annotated[list, add_messages]

    # === Context ===
    review_text: str
    rating: int
    review_context: ReviewAnalysis
    product_context: ProductContext
    customer_context: CustomerContext
    dialog_history: list[dict[str, str]]

    # === Decisions ===
    current_stage: CaseStage
    next_stage: CaseStage
    strategy: str
    ai_response: str
    should_escalate: bool

    # === Actions ===
    actions: list[ActionItem]
    execution_results: list[ExecutionResult]

    # === Memory ===
    short_term_facts: str
    relevant_history: str
    similar_cases: list[dict[str, Any]]

    # === Metadata ===
    is_managed_by_human: bool
    manager_id: Optional[int]
    error: Optional[str]
    retry_count: int


class AgentContext(TypedDict, total=False):
    """Configuration context for agents.

    Passed via runtime context for configurable behavior.
    """

    # LLM Configuration
    primary_model: str
    secondary_model: str
    temperature: float
    max_tokens: int

    # API Keys (loaded from environment)
    google_api_key: str
    langsmith_api_key: str

    # Feature flags
    enable_memory: bool
    enable_escalation: bool
    enable_logging: bool

    # Thresholds
    escalation_threshold: float
    max_compensation: int
    min_rating_for_auto: int
