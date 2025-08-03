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


user_info_to_get = "private name and age"

def UserInfoValidator(messages):
    messages_str = "\n".join([f"{msg.type}: {msg.content}" for msg in messages if msg.type == "human"])
    prompt = f"""you need to return True if *all* the next information is in the next conversation, otherwise return False. DROP EXPLANATION. 
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
    elif "competition" in last_response:
        return "CompetitionEngine"
    elif "outcome" in last_response:
        return "OutcomeEngine"
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
        return {"messages": response,"info_complete": True}
    else:
        return {"messages": response,"info_complete": False}

def MessagingEngine(state: MyState):
    new_message = AIMessage(content="Welcome to Messaging Engine")
    return {"messages": new_message}

def ContentEngine(state: MyState):
    new_message = AIMessage(content="Welcome to Content Engine")
    return {"messages": new_message}

def OutcomeEngine(state: MyState):
    new_message = AIMessage(content="Welcome to Outcome Engine")
    return {"messages": new_message}

def CompetitionEngine(state: MyState):
    new_message = AIMessage(content="Welcome to Competition Engine")
    return {"messages": new_message}

def EngineRouter(state: MyState):
    system_message = SystemMessage(content="""
        You need to decide to which engine to route the user based on age.
        Rules:
        - If the user is under 13 → route to ContentEngine
        - If the user is between 13 and 17 → route to OutcomeEngine
        - If the user is between 18 and 24 → route to CompetitionEngine
        - If the user is 25 or older → route to MessagingEngine
        Return the engine name only (ContentEngine / OutcomeEngine / CompetitionEngine / MessagingEngine).
        """)
    messages = [system_message] + state["messages"]
    response = llm.invoke(messages)
    new_messages = state["messages"] + [response]
    return {
        "messages": new_messages,  # Update state
        "info_complete": state["info_complete"]  # Pass-through
    }

# graph builder
graph_builder = StateGraph(MyState)

# nodes
graph_builder.add_node("MarketingMachine", MarketingMachine)
graph_builder.add_node("MessagingEngine", MessagingEngine)
graph_builder.add_node("ContentEngine", ContentEngine)
graph_builder.add_node("OutcomeEngine", OutcomeEngine)
graph_builder.add_node("CompetitionEngine", CompetitionEngine)
graph_builder.add_node("EngineRouter", EngineRouter)


# edges
graph_builder.add_edge(START, "MarketingMachine")
graph_builder.add_edge("MessagingEngine", END)
graph_builder.add_edge("ContentEngine", END)
graph_builder.add_edge("OutcomeEngine", END)
graph_builder.add_edge("CompetitionEngine", END)

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
        "ContentEngine": "ContentEngine",
        "OutcomeEngine": "OutcomeEngine",
        "CompetitionEngine": "CompetitionEngine"
    }
)

# compile
graph = graph_builder.compile()
