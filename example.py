from langgraph_sdk import get_sync_client

c = get_sync_client(url="http://localhost:2024")

t = c.threads.create()
r = c.runs.wait(
    thread_id=t["thread_id"], assistant_id="agent", input={"changeme": "Foo"}
)
print(r)
