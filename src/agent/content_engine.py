from langchain_core.messages import AIMessage
from typing import Annotated
from langgraph.graph.message import add_messages
from typing import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph import StateGraph, START, END

class ContentEngineState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    chosen_engine: str
    info_complete: bool

WELCOME_MESSAGE = """Welcome to Content Engine

We can can create a number of different content items, including:

One-pager
Customer case study
eBook
Blog, article
Campaign bill of materials

Which type of content do we want to create?

"""

def ContentEngineNode(state: ContentEngineState):
    new_message = AIMessage(content=WELCOME_MESSAGE)
    return {"messages": new_message}


subgraph_builder = StateGraph(ContentEngineState)

subgraph_builder.add_node("ContentEngineNode", ContentEngineNode)

subgraph_builder.add_edge(START, "ContentEngineNode")

ContentEngineSubgraph = subgraph_builder.compile()