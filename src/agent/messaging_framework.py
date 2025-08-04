from langchain_core.messages import AIMessage
from typing import Annotated
from langgraph.graph.message import add_messages
from typing import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph import StateGraph, START, END

class MessagingEngineState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    info_complete: bool
    chosen_engine: str

WELCOME_MESSAGE = """Welcome to Messaging Framework
We can create a variety of messaging frameworks, including:

Audience-based messaging
Account-based messaging
Industry-based messaging
Product-based messaging
Combination

Which type of messaging do we want to create?
"""

def MessagingEngineNode(state: MessagingEngineState):
    new_message = AIMessage(content=WELCOME_MESSAGE)
    return {"messages": new_message}


subgraph_builder = StateGraph(MessagingEngineState)

subgraph_builder.add_node("MessagingEngineNode", MessagingEngineNode)

subgraph_builder.add_edge(START, "MessagingEngineNode")

MessagingEngineSubgraph = subgraph_builder.compile()