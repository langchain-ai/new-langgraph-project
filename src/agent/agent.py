from typing import Annotated
from langgraph.graph.message import add_messages
from typing import TypedDict
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, AIMessage
from agent.PROMPTS import MarketingMachinePrompt, UserInfoValidatorPrompt
from agent.messaging_framework import MessagingEngineSubgraph
from agent.competitive_analysis import CompetitiveAnalysisSubgraph
from agent.marketing_research import MarketingResearchSubgraph
from agent.content_engine import ContentEngineSubgraph
from langgraph.types import Command


"LLM"
llm = init_chat_model(model="openai:gpt-4o")

"Graph State"
class MyState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    chosen_engine: str
    info_complete: bool


# Helper Functions:
def MarketingMachineInfoValidator(messages):
    messages_str = "\n".join([f"{msg.type}: {msg.content}" for msg in messages])# if msg.type == "human"])
    prompt = UserInfoValidatorPrompt.format(messages_str)
    response = llm.invoke(prompt)
    if "true" in response.content.lower():
        return True
    else:
        return False

# Routing Functions:    
def routing_function_2(state: MyState):
    last_response = state.get("chosen_engine", "Undefined")
    if "messaging" in last_response:
        return "MessagingEngine"
    elif "competition" in last_response:
        return "CompetitiveAnalysis"
    elif "research" in last_response:
        return "MarketingResearch"
    elif "content" in last_response:
        return "ContentEngine" 
    elif "undefined" in last_response:
        return "END"

def routing_function_1(state: MyState):
    if state["info_complete"]:
        return "MarketingMachineRouter"
    else:
        return "END"

# Nodes:
def MarketingMachineWelcome(state: MyState):
    if state.get("chosen_engine") == "MessagingEngine":
        return Command(
            update = {"messages": state["messages"]},
            goto = "MessagingEngine"
        )
    elif state.get("chosen_engine") == "CompetitiveAnalysis":
        return Command(
            update = {"messages": state["messages"]},
            goto = "CompetitiveAnalysis"
        )
    elif state.get("chosen_engine") == "MarketingResearch":
        return Command(
            update = {"messages": state["messages"]},
            goto = "MarketingResearch"
        )
    elif state.get("chosen_engine") == "ContentEngine":
        return Command(
            update = {"messages": state["messages"]},
            goto = "ContentEngine"
        )

    else:
        system_message = SystemMessage(content=MarketingMachinePrompt)
        messages = [system_message] + state["messages"]
        response = llm.invoke(messages)
        if MarketingMachineInfoValidator(messages):
            return {"info_complete": True}
        else:
            return {"messages": response,"info_complete": False}

def MarketingMachineRouter(state: MyState):
    system_message = SystemMessage(content="""
        You need to decide to which engine to route the user
        Rules:
            if project name begins with 'a'-'f', route to MessagingEngine
            if project name begins with 'g'-'l', route to CompetitiveAnalysis
            if project name begins with 'm'-'r', route to MarketingResearch
            if project name begins with 's'-'z', route to ContentEngine
        Return the engine name only. DROP EXPLANATION.
        """)
    messages = [system_message] + state["messages"]
    response = llm.invoke(messages)
    return { 
        "chosen_engine": response.content.lower(), 
    }



# graph builder
graph_builder = StateGraph(MyState)

# nodes
graph_builder.add_node("MarketingMachineWelcome", MarketingMachineWelcome)
graph_builder.add_node("MarketingMachineRouter", MarketingMachineRouter)
graph_builder.add_node("MessagingEngine", MessagingEngineSubgraph)
graph_builder.add_node("CompetitiveAnalysis", CompetitiveAnalysisSubgraph)
graph_builder.add_node("MarketingResearch", MarketingResearchSubgraph)
graph_builder.add_node("ContentEngine", ContentEngineSubgraph)


# edges
graph_builder.add_edge(START, "MarketingMachineWelcome")
graph_builder.add_edge("ContentEngine", END)


graph_builder.add_conditional_edges(
    "MarketingMachineWelcome",
    routing_function_1,
    {
        "MarketingMachineRouter": "MarketingMachineRouter",
        "END": END
    }
)
graph_builder.add_conditional_edges(
    "MarketingMachineRouter",
    routing_function_2,
    {
        "MessagingEngine": "MessagingEngine",
        "ContentEngine": "ContentEngine",
        "CompetitiveAnalysis": "CompetitiveAnalysis",
        "MarketingResearch": "MarketingResearch"
    }
)

# compile
graph = graph_builder.compile()
