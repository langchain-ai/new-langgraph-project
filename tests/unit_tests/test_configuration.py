"""Unit tests for 5STARS agent configuration and state."""

from langgraph.pregel import Pregel

from agent import CaseStage, CaseState, graph
from agent.state import IssueSeverity, ReviewAnalysis


def test_graph_is_compiled() -> None:
    """Test that the graph is properly compiled."""
    assert isinstance(graph, Pregel)


def test_case_stage_enum() -> None:
    """Test CaseStage enum values."""
    assert CaseStage.RECEIVED.value == "received"
    assert CaseStage.ANALYSIS.value == "analysis"
    assert CaseStage.COMPENSATION_OFFER.value == "compensation_offer"
    assert CaseStage.ESCALATION.value == "escalation"
    assert CaseStage.RESOLVED.value == "resolved"


def test_issue_severity_enum() -> None:
    """Test IssueSeverity enum values."""
    assert IssueSeverity.LOW.value == "low"
    assert IssueSeverity.MEDIUM.value == "medium"
    assert IssueSeverity.HIGH.value == "high"
    assert IssueSeverity.CRITICAL.value == "critical"


def test_case_state_structure() -> None:
    """Test CaseState TypedDict structure."""
    state: CaseState = {
        "case_id": 123,
        "chat_id": "chat_456",
        "review_text": "Test review",
        "rating": 2,
        "current_stage": CaseStage.RECEIVED,
        "messages": [],
        "dialog_history": [],
        "actions": [],
        "execution_results": [],
        "is_managed_by_human": False,
    }
    assert state["case_id"] == 123
    assert state["rating"] == 2
    assert state["current_stage"] == CaseStage.RECEIVED


def test_review_analysis_structure() -> None:
    """Test ReviewAnalysis TypedDict structure."""
    analysis: ReviewAnalysis = {
        "primary_issue": "quality",
        "issue_severity": IssueSeverity.MEDIUM,
        "sentiment": "frustrated",
        "suggested_compensation": 300,
        "needs_manager": False,
        "key_facts": ["товар не соответствует описанию"],
    }
    assert analysis["primary_issue"] == "quality"
    assert analysis["suggested_compensation"] == 300
