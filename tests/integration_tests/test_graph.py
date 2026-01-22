"""Integration tests for 5STARS agent graph."""

import pytest

from agent import CaseStage, graph, process_case

pytestmark = pytest.mark.anyio


@pytest.fixture
def sample_review_state():
    """Create a sample review state for testing."""
    return {
        "case_id": 1,
        "chat_id": 1,
        "review_text": "Товар пришёл бракованный, качество ужасное. Очень разочарован покупкой.",
        "rating": 2,
        "current_stage": CaseStage.RECEIVED,
        "messages": [],
        "dialog_history": [],
        "actions": [],
        "execution_results": [],
        "is_managed_by_human": False,
        "retry_count": 0,
    }


@pytest.mark.langsmith
async def test_graph_basic_invocation(sample_review_state) -> None:
    """Test that the graph can be invoked with basic state."""
    res = await graph.ainvoke(sample_review_state)
    assert res is not None
    # Check that key fields are present
    assert "next_stage" in res or "current_stage" in res
    assert "messages" in res


@pytest.mark.langsmith
async def test_graph_processes_negative_review(sample_review_state) -> None:
    """Test graph processing of a negative review."""
    sample_review_state["rating"] = 1
    sample_review_state["review_text"] = "Полный обман! Товар не соответствует описанию!"

    res = await graph.ainvoke(sample_review_state)

    assert res is not None
    # Should have generated some response or escalation
    assert "ai_response" in res or res.get("should_escalate") is True


@pytest.mark.langsmith
async def test_process_case_convenience_function() -> None:
    """Test the process_case convenience function."""
    result = await process_case(
        case_id=100,
        review_text="Размер не подошёл, товар маломерит.",
        rating=3,
        chat_id="test_chat_456",
        customer_name="Иван",
    )

    assert result is not None
    assert result.get("case_id") == 100


@pytest.mark.langsmith
async def test_graph_with_customer_context(sample_review_state) -> None:
    """Test graph with customer context."""
    sample_review_state["customer_context"] = {
        "customer_id": "cust_789",
        "customer_name": "Мария",
        "total_orders": 10,
        "total_reviews": 5,
        "average_rating": 4.2,
    }

    res = await graph.ainvoke(sample_review_state)

    assert res is not None


@pytest.mark.langsmith
async def test_graph_with_product_context(sample_review_state) -> None:
    """Test graph with product context."""
    sample_review_state["product_context"] = {
        "product_id": "prod_123",
        "product_name": "Кроссовки спортивные",
        "category": "Обувь",
        "price": 3500.0,
        "seller_id": "seller_456",
    }

    res = await graph.ainvoke(sample_review_state)

    assert res is not None
