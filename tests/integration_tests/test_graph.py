import pytest
from langsmith import expect, unit

from agent import graph


@pytest.mark.asyncio
@unit
async def test_agent_simple_passthrough() -> None:
    res = await graph.ainvoke({"messages": ["user", "What's 62 - 19?"]})
    expect(str(res["messages"][-1].content)).to_contain("43")
