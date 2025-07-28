from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_stream_writer

import asyncio
import os
from openai import OpenAI
from dotenv import load_dotenv
from .utils import chat_cache, SYSTEM_PROMPT

# Load environment variables from .env file
load_dotenv()




app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def stream_response(client_id: str):
    
    stream = client.responses.create(
        model="gpt-4.1",
        input=chat_cache[client_id],
        stream=True,
    )

    assistant_chunks: list[str] = []
    # `stream` is a *regular* (sync) iterator → use `for`, not `async for`
    for event in stream:
        if event.type == "response.output_text.delta":
            chunk = event.delta                    # str, e.g. "H"
            if chunk:
                assistant_chunks.append(chunk)
                yield chunk.encode("utf-8")        # << HERE
                #await asyncio.sleep(0.005)

    full_reply = "".join(assistant_chunks)
    chat_cache[client_id].append({"role": "assistant", "content": full_reply})


class State(TypedDict):
    messages: Annotated[list, add_messages]
    client_id: str

def chatbot(state: State):
    writer = get_stream_writer()
    client_id = state["client_id"]
    history = chat_cache[client_id]
    # Stream chunks from OpenAI client
    stream = client.responses.create(
        model="gpt-4.1",
        input=history,
        stream=True,
    )
    assistant_chunks = []
    for event in stream:
        if event.type == "response.output_text.delta":
            chunk = event.delta
            if chunk:
                print(chunk)
                #writer({"token": chunk})   # << LangGraph will yield this chunk outward
                writer(chunk)
                assistant_chunks.append(chunk)

    full_reply = "".join(assistant_chunks)
    chat_cache[client_id].append({"role": "assistant", "content": full_reply})
    # Return the updated state
    state["messages"] = history
    return state

graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph = graph_builder.compile(checkpointer=MemorySaver())


@app.post("/chat/{session_id}")
async def chat(session_id: str, request: Request):
    try:
        body = await request.json()
        user_msg:  str | None = body.get("message")
        client_id: str | None = body.get("client_id")

        if not client_id or not user_msg:
            raise HTTPException(status_code=400,
                                detail="Fields 'client_id' and 'message' are required.")
        
        if client_id not in chat_cache:
            chat_cache[client_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        # Add user message to cache
        chat_cache[client_id].append({"role": "user", "content": user_msg})

        config = {"configurable": {"thread_id": client_id}}
        
        # return graph.stream({"client_id": client_id}, config=config)
        #return StreamingResponse(
        #    stream_response(client_id),
        #    media_type="text/plain; charset=utf-8"
        #)
        return StreamingResponse(
            graph.stream({"client_id": client_id}, config=config, stream_mode="custom"),
            media_type="text/plain; charset=utf-8"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    