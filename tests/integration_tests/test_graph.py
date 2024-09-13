import pytest
from langsmith import unit

from agent import graph


@pytest.mark.asyncio
@unit
async def test_agent_simple_passthrough() -> None:
    res = await graph.ainvoke(
        {"messages": [("user", "Who is the founder of LangChain?")]}
    )

    assert "harrison" in str(res["messages"][-1].content).lower()
