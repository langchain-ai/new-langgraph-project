import pytest
from langgraph_sdk import get_client


@pytest.mark.asyncio
async def test_serialization():
    """Test that it runs to completion."""
    client = get_client(url="http://localhost:2024")
    t = await client.threads.create()
    chunks = client.runs.stream(
        thread_id=t["thread_id"],
        assistant_id="agent",
        input={
            "foo": {
                "bar": {
                    "baz": "BUZZ",
                    "messages": [{"type": "human", "content": "hi there"}],
                }
            }
        },
    )
    async for c in chunks:
        if c.event == "error":
            raise c.data
