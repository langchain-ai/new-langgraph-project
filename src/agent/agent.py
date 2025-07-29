from typing import Annotated
from langgraph.graph.message import add_messages
from typing import TypedDict
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, AIMessage
"LLM"
llm = init_chat_model(model="openai:gpt-4o-mini")

"Graph State"
class MyState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    info_complete: bool


user_info_to_get = ["user name", "user age"]

def UserInfoValidator(messages):
    messages_str = "\n".join([f"{msg.type}: {msg.content}" for msg in messages if msg.type == "human"])
    prompt = f"""you need to return True if *all* the next information is inside the messages, otherwise return False. DROP EXPLANATION. 
        The user info to get is: {user_info_to_get}.
        The messages are: {messages_str}"""
    response = llm.invoke(prompt)
    if "true" in response.content.lower():
        return True
    else:
        return False
    
def engine_decision_router(state: MyState):
    last_response = state["messages"][-1].content.lower()
    if "messaging" in last_response:
        return "MessagingEngine"
    else:
        return "ContentEngine"  

def routing_function(state: MyState):
    if state["info_complete"]:
        return "EngineRouter"
    else:
        return "END"

def MarketingMachine(state: MyState):
    system_message = SystemMessage(content=f"You need to get the information about the user before you start the conversation. The user info to get is: {user_info_to_get}")
    messages = [system_message] + state["messages"]
    response = llm.invoke(messages)
    if UserInfoValidator(messages):
        return {"messages": [response],"info_complete": True}
    else:
        return {"messages": [response],"info_complete": False}

def MessagingEngine(state: MyState):
    new_message = AIMessage(content="Welcome to Messaging Engine")
    return {"messages": [new_message]}

def ContentEngine(state: MyState):
    new_message = AIMessage(content="Welcome to Content Engine")
    return {"messages": [new_message]}

def EngineRouter(state: MyState):
    system_message = SystemMessage(content=f"Based on the user age you need to decide to which engine you need to route the user if you user is under 18 you need to route to the ContentEngine, otherwise you need to route to the MessagingEngine. Return the engine name only.")
    messages = [system_message] + state["messages"]
    response = llm.invoke(messages)
    new_messages = state["messages"] + [response]
    return {
        "messages": new_messages,  # Update state
        "info_complete": state["info_complete"]  # Pass-through
    }

graph_builder = StateGraph(MyState)
# nodes
graph_builder.add_node("MarketingMachine", MarketingMachine)
graph_builder.add_node("MessagingEngine", MessagingEngine)
graph_builder.add_node("ContentEngine", ContentEngine)
graph_builder.add_node("EngineRouter", EngineRouter)

# edges
graph_builder.add_edge(START, "MarketingMachine")
graph_builder.add_edge("MessagingEngine", END)
graph_builder.add_edge("ContentEngine", END)

# conditional edges
graph_builder.add_conditional_edges(
    "MarketingMachine",
    routing_function,
    {
        "EngineRouter": "EngineRouter",
        "END": END
    }
)

graph_builder.add_conditional_edges(
    "EngineRouter",
    engine_decision_router,
    {
        "MessagingEngine": "MessagingEngine",
        "ContentEngine": "ContentEngine"
    }
)

# compile
graph = graph_builder.compile()
