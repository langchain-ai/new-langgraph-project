"""Integration tests for 5STARS agent graph."""

import pytest

from agent import graph

pytestmark = pytest.mark.anyio


@pytest.fixture
def sample_review_state():
    """Create a sample review state for testing."""
    return {
        "review_text": "Товар пришёл бракованный, качество ужасное. Очень разочарован покупкой.",
        "rating": 2,
        "pros": "",
        "cons": "Сломался",
        "product_name": "Тестовый товар",
        "order_date": "2024-01-15",
        "customer_name": "Тестовый клиент",
        "dialog_history": [],
        "messages": [],
    }


@pytest.mark.langsmith
async def test_graph_basic_invocation(sample_review_state) -> None:
    """Test that the graph can be invoked with basic state."""
    res = await graph.ainvoke(sample_review_state)
    assert res is not None
    # Check that messages were generated
    assert "messages" in res
    assert len(res["messages"]) > 0


@pytest.mark.langsmith
async def test_graph_processes_negative_review(sample_review_state) -> None:
    """Test graph processing of a negative review."""
    sample_review_state["rating"] = 1
    sample_review_state["review_text"] = "Полный обман! Товар не соответствует описанию!"

    res = await graph.ainvoke(sample_review_state)

    assert res is not None
    # Should have analysis and messages
    assert "analysis" in res
    assert "messages" in res


@pytest.mark.langsmith
async def test_graph_processes_positive_review(sample_review_state) -> None:
    """Test graph processing of a positive review."""
    sample_review_state["rating"] = 5
    sample_review_state["review_text"] = "Отличный товар! Быстрая доставка, качество супер!"
    sample_review_state["pros"] = "Качество, доставка"
    sample_review_state["cons"] = ""

    res = await graph.ainvoke(sample_review_state)

    assert res is not None
    assert "analysis" in res
    assert "messages" in res


@pytest.mark.langsmith
async def test_graph_with_customer_name(sample_review_state) -> None:
    """Test graph with customer name."""
    sample_review_state["customer_name"] = "Мария"

    res = await graph.ainvoke(sample_review_state)

    assert res is not None
    assert "messages" in res


@pytest.mark.langsmith
async def test_graph_with_product_context(sample_review_state) -> None:
    """Test graph with product context."""
    sample_review_state["product_name"] = "Кроссовки спортивные"

    res = await graph.ainvoke(sample_review_state)

    assert res is not None
    assert "messages" in res
