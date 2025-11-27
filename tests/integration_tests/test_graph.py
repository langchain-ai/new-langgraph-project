import pytest

from agent import graph

pytestmark = pytest.mark.anyio


@pytest.mark.langsmith
async def test_auditor_agent_basic_response() -> None:
    """Test that the auditor agent can handle a simple message."""
    inputs = {
        "messages": [
            {"role": "user", "content": "Hello, can you help me with an audit question?"}
        ]
    }
    res = await graph.ainvoke(inputs)

    assert res is not None
    assert "messages" in res
    assert len(res["messages"]) > 1  # Should have user message + agent response


@pytest.mark.langsmith
async def test_auditor_with_coder_coordination() -> None:
    """Test that the auditor can coordinate with the coder agent."""
    inputs = {
        "messages": [
            {"role": "user", "content": "Can you test the database connection?"}
        ]
    }
    res = await graph.ainvoke(inputs)

    assert res is not None
    assert "messages" in res
    # Should have multiple messages from the coordination
    assert len(res["messages"]) >= 2
