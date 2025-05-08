import pytest

from agent import graph


@pytest.mark.langsmith
async def test_agent_simple_passthrough() -> None:
    res = await graph.ainvoke({"changeme": "some_val"})
    assert res is not None
