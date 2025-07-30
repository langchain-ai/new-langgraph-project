Here’s a clean, production-ready README.md that explains how to authenticate, create a thread, and run your LangGraph agent using the notebook code you provided:

⸻


# 🧠 LangGraph Agent Client Example

This notebook demonstrates how to connect to a deployed LangGraph agent, create a conversation thread, and stream its output using the LangGraph SDK.

---

## ✅ Prerequisites

- A deployed LangGraph agent with a known `graph_id` (e.g. `"agent"`)
- A registered assistant created for that graph (can be `"agent"` or a UUID)
- A valid API key for LangGraph Cloud or local runtime
- Python 3.10+
- `.env` file with the following variables:

```env
LANGGRAPH_PLATFORM_URL=https://YOUR-ENV.langgraph.app
LANGGRAPH_PLATFORM_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

You can find your assistant ID and graph name using:

client.assistants.search()



⸻

📦 Install Dependencies

pip install langgraph-sdk python-dotenv


⸻

🚀 Code Overview

1. Load Environment

import os
from dotenv import load_dotenv
load_dotenv()


⸻

2. Initialize Client

from langgraph_sdk import get_sync_client

client = get_sync_client(
    url=os.getenv("LANGGRAPH_PLATFORM_URL"),
    api_key=os.getenv("LANGGRAPH_PLATFORM_API_KEY")
)


⸻

3. Create a Thread

thread = client.threads.create()
print("Thread ID:", thread["thread_id"])


⸻

4. Run Agent (Streaming)

⚠️ Note: The assistant ID must match an active deployed assistant (e.g. "agent")

import asyncio
from langgraph_sdk import get_client

client2 = get_client(
    url=os.getenv("LANGGRAPH_PLATFORM_URL"),
    api_key=os.getenv("LANGGRAPH_PLATFORM_API_KEY")
)

thread2 = await client2.threads.create()

async def main():
    async for chunk in client2.runs.stream(
        thread_id=thread2["thread_id"],
        assistant_id="agent",  # or your actual assistant UUID
        input={
            "messages": [{"role": "human", "content": "hi"}]
        },
        stream_mode="updates"
    ):
        print(chunk.data)

await main()


⸻

💡 Troubleshooting
	•	422 Unprocessable Entity: Make sure the assistant_id matches a registered assistant.
	•	ModuleNotFoundError: Check that all required libraries are installed in your virtual environment.
	•	asyncio.run(...) error in notebooks? Use await main() instead of asyncio.run(main()).

⸻

📚 References
	•	LangGraph SDK Docs
	•	LangGraph Cloud Console

---

Let me know if you want a shell script (`run.sh`) or `.ipynb` version for easier sharing.