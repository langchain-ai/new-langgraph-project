from langchain_core.messages import AIMessage
from typing import Annotated
from langgraph.graph.message import add_messages
from typing import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph import StateGraph, START, END

class MarketingResearchState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    chosen_engine: str
    info_complete: bool

WELCOME_MESSAGE = """Welcome to Marketing Research

We can perform a variety of marketing research, including:

A specific company (e.g., Bank of America)
Industry (e.g., Financial Services Industry) 
Audience (e.g., Chief Information Officer)
Actual person (e.g., the CIO of Bank America)


Which type of research do we want to perform?
"""

def MarketingResearchNode(state: MarketingResearchState):
    new_message = AIMessage(content=WELCOME_MESSAGE)
    return {"messages": new_message}


subgraph_builder = StateGraph(MarketingResearchState)

subgraph_builder.add_node("MarketingResearchNode", MarketingResearchNode)

subgraph_builder.add_edge(START, "MarketingResearchNode")

MarketingResearchSubgraph = subgraph_builder.compile()