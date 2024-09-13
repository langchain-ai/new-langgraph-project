import pytest
from agent import graph
from langsmith import expect, unit


@pytest.mark.asyncio
@unit
async def test_agent_simple_passthrough() -> None:
    res = await graph.ainvoke(
        {"messages": [{"role": "user", "content": "What's 62 - 19?"}]}
    )
    expect(res["messages"][-1]["content"][0]["text"]).to_contain("43")
