from langchain_core.messages import AIMessage
from typing import Annotated
from langgraph.graph.message import add_messages
from typing import TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph import StateGraph, START, END

class CompetitiveAnalysisState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    chosen_engine: str
    info_complete: bool

WELCOME_MESSAGE = """Welcome to Competitive Analysis
Who are the competitors we want to analyze? 

Competitor name__________________
What are the priorities of this competitive analysis? _______________________
Do you want to focus on a particular product/service area? Or the entire company? ______________________
Websites you want to include in the competitive analysis: (can include more than one now)_________________
Would you like for us to look for specific keywords or terms that the competitor is using or that you want to use? ____________________
Are there any special instructions or things to keep in mind during the competitive analysis? ____________________

Do you have any reference materials you want to include?
[Upload files/links]

Would you like to add another competitor?
[repeat above flow]

Would you like me to rerun the analysis periodically?
	Recurring analysis parameters 


"""

def CompetitiveAnalysisNode(state: CompetitiveAnalysisState):
    new_message = AIMessage(content=WELCOME_MESSAGE)
    return {"messages": new_message}


subgraph_builder = StateGraph(CompetitiveAnalysisState)

subgraph_builder.add_node("CompetitiveAnalysisNode", CompetitiveAnalysisNode)

subgraph_builder.add_edge(START, "CompetitiveAnalysisNode")

CompetitiveAnalysisSubgraph = subgraph_builder.compile()