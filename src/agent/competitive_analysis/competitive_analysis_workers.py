from langgraph.graph import StateGraph,START, END
from src.agent.competitive_analysis.models import CompetitiveAnalysisState, WorkerState
from langchain_core.messages import SystemMessage, AIMessage
from langchain.chat_models import init_chat_model
from tavily import TavilyClient
import os
from src.agent.competitive_analysis.utils import fetch_with_urls, fetch_with_web_search
from src.agent.competitive_analysis.prompts import HEADLINE_PROMPT, HEADLINE_SYSTEM_PROMPT
from src.agent.competitive_analysis.models import MainIdeaAndHeadline

llm = init_chat_model(model="openai:gpt-4o")
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

def fetch_documents(state: WorkerState):
    """Worker writes a section of the report"""

    current_competitor = state['competitor']

    # Documents
    if current_competitor.websites:
        documents = fetch_with_urls(current_competitor.websites)
    else:
        query = f"{current_competitor.competitor_name} {current_competitor.focus_product_or_service}"
        documents = fetch_with_web_search(query)
    
    current_competitor.documents.extend(documents)

    return {"competitor": current_competitor}

def generate_headline(state: WorkerState):
    """Worker writes a section of the report"""

    current_competitor = state['competitor']

    headline_prompt = HEADLINE_PROMPT.format(company_name=current_competitor.competitor_name, product_name=current_competitor.focus_product_or_service, product_text=str(current_competitor.documents))
    headline_messages = [SystemMessage(content=HEADLINE_SYSTEM_PROMPT), AIMessage(content=headline_prompt)]
    llm_with_structured_output = llm.with_structured_output(MainIdeaAndHeadline)
    ai_message = llm_with_structured_output.invoke(headline_messages)
    current_competitor.main_idea_and_headline = ai_message

    return {"competitor": current_competitor, "completed_competitors": [current_competitor]}


builder = StateGraph(WorkerState)

builder.add_node("fetch_documents", fetch_documents)
builder.add_node("generate_headline", generate_headline)

builder.add_edge(START, "fetch_documents")
builder.add_edge("fetch_documents", "generate_headline")
builder.add_edge("generate_headline", END)

CompetitiveAnalysisWorkerGraph = builder.compile()