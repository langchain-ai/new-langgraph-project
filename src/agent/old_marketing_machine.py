from typing import Annotated, Literal
from langgraph.graph.message import add_messages
from typing import TypedDict
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import SystemMessage, AIMessage
from agent.PROMPTS import MarketingMachinePrompt, UserInfoValidatorPrompt, MarketingMachineExplicitRoutingPrompt, MarketingMachineImplicitRoutingPrompt
from agent.messaging_framework import MessagingEngineSubgraph
from agent.competitive_analysis import CompetitiveAnalysisSubgraph
from agent.marketing_research import MarketingResearchSubgraph
from agent.content_engine import ContentEngineSubgraph
from langgraph.types import Command
from pydantic import BaseModel

"LLM"
llm = init_chat_model(model="openai:gpt-4o")

"Graph State"
class MyState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    info_complete: bool
    button_pressed: Literal[
        "MessagingEngine", "CompetitiveAnalysis", "MarketingResearch", "ContentEngine", "Not Pressed"
    ]


class ExplicitRoutingOutput(BaseModel):
    engine: Literal["MessagingEngine", "CompetitiveAnalysis", "MarketingResearch", "ContentEngine", "Not Applicable"]
    validation_message: str

def ButtonRouting(state: MyState):
    if state.get("button_pressed") == "MessagingEngine":
        return "MessagingEngine"
    elif state.get("button_pressed") == "CompetitiveAnalysis":
        return "CompetitiveAnalysis"
    elif state.get("button_pressed") == "MarketingResearch":
        return "MarketingResearch"
    elif state.get("button_pressed") == "ContentEngine":
        return "ContentEngine"
    else:
        return False

def ExplicitRouting(state: MyState):
    system_message = SystemMessage(content=MarketingMachineExplicitRoutingPrompt)
    messages = [system_message] + state["messages"]
    response = llm.invoke(messages)
    if "false" in response.content.lower():
        return False
    elif "messaging" in response.content.lower():
        return "MessagingEngine"
    elif "competition" in response.content.lower():
        return "CompetitiveAnalysis"
    elif "research" in response.content.lower():
        return "MarketingResearch"
    elif "content" in response.content.lower():
        return "ContentEngine" 
    else:
        return False
    
def ImplicitRouting(state: MyState):
    system_message = SystemMessage(content=MarketingMachineImplicitRoutingPrompt)
    messages = [system_message] + state["messages"]
    response = llm.with_structured_output(ExplicitRoutingOutput, messages)
    if response.engine == "Not Applicable":
        return {"messages": [AIMessage(content=response.validation_message)]}
    else:
        return {"messages": [AIMessage(content=response.validation_message)], "chosen_engine": response.engine}

print_format = """**********
{debug_info}
**********"""

def QuestionAnswerer(state: MyState):
    system_message = SystemMessage(content="""
        You are a helpful assistant that answers questions that are in the scope of marketing. 
        if the question is not in the scope of marketing, you should say "I'm sorry, I can't answer that question."
        """)
    messages = [system_message] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [AIMessage(content=response.content)]}


# Nodes:
def MarketingMachineWelcome(state: MyState):
    
    # Case 1: Button Routing
    if ButtonRouting(state) != False:
        return Command(
            update = {"messages": state["messages"]},
            goto = ButtonRouting(state)
        ) 

    # Case 2: Explicit Routing (Get text from the user and route to the appropriate engine)
    print(print_format.format(debug_info="Explicit Routing Started"))
    if ExplicitRouting(state) != False:
        return Command(
            update = {"messages": state["messages"]},
            goto = ExplicitRouting(state)
        )
    
    else:
        return Command(
            update = {"messages": state["messages"]},
            goto = QuestionAnswerer
        )

    


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
graph_builder.add_node("MessagingEngine", MessagingEngineSubgraph)
graph_builder.add_node("CompetitiveAnalysis", CompetitiveAnalysisSubgraph)
graph_builder.add_node("MarketingResearch", MarketingResearchSubgraph)
graph_builder.add_node("ContentEngine", ContentEngineSubgraph)

# edges
graph_builder.add_edge(START, "MarketingMachineWelcome")



# compile
graph = graph_builder.compile()
