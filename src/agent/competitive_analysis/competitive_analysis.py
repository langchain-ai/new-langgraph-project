from typing import List, Optional, Literal,Annotated
from typing_extensions import TypedDict
from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, AnyMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from langgraph.types import interrupt, Command, Send
from langchain_core.documents import Document
from langchain_community.document_loaders import WebBaseLoader
from tavily import TavilyClient
import operator
from langsmith import traceable
from operator import add
import os
from src.agent.competitive_analysis.models import Competitor, Answer, PartialAnswers, QuestionResponse, MainIdeaAndHeadline, ValueProposition, CustomerBenefits, SupportBenefits, Usecases, SuccessBenefits, Keywords
from src.agent.competitive_analysis.models import CompetitorOutput
from src.agent.competitive_analysis.prompts import COMPETITOR_LIST_PROMPT, QUESTIONNAIRE_PROMPT, HEADLINE_PROMPT, HEADLINE_SYSTEM_PROMPT, VALUE_PROPOSITION_PROMPT, VALUE_PROPOSITION_SYSTEM_PROMPT, CUSTOMER_BENEFITS_PROMPT, CUSTOMER_BENEFITS_SYSTEM_PROMPT, SUPPORT_BENEFITS_PROMPT, SUPPORT_BENEFITS_SYSTEM_PROMPT, USECASES_PROMPT, USECASES_SYSTEM_PROMPT, SUCCESS_BENEFITS_PROMPT, SUCCESS_BENEFITS_SYSTEM_PROMPT, KEYWORDS_PROMPT, KEYWORDS_SYSTEM_PROMPT
from src.agent.competitive_analysis.utils import fetch_with_urls, fetch_with_web_search

llm = init_chat_model(model="openai:gpt-4o")
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

"""States"""
class CompetitiveAnalysisState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    answers: Answer
    user_answered_all_questions: bool
    competitors: list[Competitor]
    final_report: str

class WorkerState(TypedDict):
    competitor: Competitor
    completed_competitors: Annotated[list, operator.add]
    output: list

"""Node Functions"""
def update_answers(current: Answer, new_partial: PartialAnswers) -> Answer:
    """Merge new partial answers with existing complete answers"""
    updates = {}
    
    for field, value in new_partial.model_dump().items():
        if value is not None:
            if field in ['websites', 'keywords', 'reference_materials']:
                # For list fields, extend existing lists
                current_list = getattr(current, field) or []
                if isinstance(value, list):
                    updates[field] = list(set(current_list + value))  # Remove duplicates
                else:
                    updates[field] = current_list + [value] if value not in current_list else current_list
            else:
                # For string fields, update if not already set or if new value is more complete
                current_value = getattr(current, field)
                if not current_value or len(str(value)) > len(str(current_value)):
                    updates[field] = value
    
    return current.model_copy(update=updates)

def user_questionnaire(state: CompetitiveAnalysisState):

    system_message = SystemMessage(content=QUESTIONNAIRE_PROMPT)
    history = state['messages']
    messages = [system_message] + history
    
    llm_with_structured_output = llm.with_structured_output(QuestionResponse)
    response = llm_with_structured_output.invoke(messages)
    
    # Update the answers with extracted information
    current_answers = state.get('answers', Answer(
        competitors_name=[], focus_product_or_service="",
        websites=[], keywords=[], instructions="", reference_materials=[]
    ))
    
    # Merge extracted answers with existing ones
    updated_answers = update_answers(current_answers, response.extracted_answers)
    
    if not response.conversation_complete and response.next_message_with_question_and_greeting:
        new_ai_message = AIMessage(content=response.next_message_with_question_and_greeting)
        user_response = interrupt({"question": response.next_message_with_question_and_greeting})
        return {
            "messages": [new_ai_message, HumanMessage(content=user_response)],
            "answers": updated_answers,
            "user_answered_all_questions": False
        }
    
    return {
        "messages": [AIMessage(content="Thanks! All information collected.")],
        "answers": updated_answers,
        "user_answered_all_questions": True
    }

def finish_questionnaire(state: CompetitiveAnalysisState) -> Literal["continue_questions", "finished"]:
    if not state.get("user_answered_all_questions", False):
        return "continue_questions"
    else:
        return "finished"

def orchestrate_competitive_analysis(state: CompetitiveAnalysisState):
    answer = state['answers']
    competitors = []
    llm_with_structured_output = llm.with_structured_output(Competitor)
    for competitor_name in answer.competitors_name:
        prompt_with_competitor_name = COMPETITOR_LIST_PROMPT.format(CompetitorNamePlaceholder=competitor_name, UserInputPlaceholder=answer, CompetitorPlaceholder=Competitor.model_json_schema())
        response = llm_with_structured_output.invoke(prompt_with_competitor_name)
        # Insert all but documents into the competitor
        competitor = Competitor(
            competitor_name=response.competitor_name,
            focus_product_or_service=response.focus_product_or_service,
            websites=response.websites if response.websites else [],
            documents=[]
        )
        competitors.append(competitor)
    return {"competitors": competitors}

def assign_workers(state: CompetitiveAnalysisState):
    """Assign a worker to each section in the plan"""

    # Kick off section writing in parallel via Send() API
    return [Send("competitive_analysis", {"competitor": s}) for s in state["competitors"]]

def competitive_analysis(state: WorkerState):
    """Worker writes a section of the report"""

    current_competitor = state['competitor']
    
    # Documents if empty or try failed fetch with web search
    if current_competitor.websites and len(current_competitor.websites) > 0:
        try:
            documents = fetch_with_urls(current_competitor.websites)
        except Exception as e:
            print(f"Error fetching documents with urls: {e}")
            query = f"{current_competitor.competitor_name} {current_competitor.focus_product_or_service}"
            documents = fetch_with_web_search(query)
    else:
        query = f"{current_competitor.competitor_name} {current_competitor.focus_product_or_service}"
        documents = fetch_with_web_search(query)

    current_competitor.documents.extend(documents)

    # Headline
    headline_prompt = HEADLINE_PROMPT.format(company_name=current_competitor.competitor_name, product_name=current_competitor.focus_product_or_service, product_text=str(current_competitor.documents))
    headline_messages = [SystemMessage(content=HEADLINE_SYSTEM_PROMPT), AIMessage(content=headline_prompt)]
    llm_with_structured_output = llm.with_structured_output(MainIdeaAndHeadline)
    ai_message = llm_with_structured_output.invoke(headline_messages)
    current_competitor.main_idea_and_headline = ai_message

    # Value proposition
    value_proposition_prompt = VALUE_PROPOSITION_PROMPT.format(company_name=current_competitor.competitor_name, product_name=current_competitor.focus_product_or_service, product_text=str(current_competitor.documents))
    value_proposition_messages = [SystemMessage(content=VALUE_PROPOSITION_SYSTEM_PROMPT), AIMessage(content=value_proposition_prompt)]
    llm_with_structured_output = llm.with_structured_output(ValueProposition)
    ai_message = llm_with_structured_output.invoke(value_proposition_messages)
    current_competitor.value_proposition = ai_message.value_proposition

    # Customer benefits
    customer_benefits_prompt = CUSTOMER_BENEFITS_PROMPT.format(company_name=current_competitor.competitor_name, product_name=current_competitor.focus_product_or_service, product_text=str(current_competitor.documents))
    customer_benefits_messages = [SystemMessage(content=CUSTOMER_BENEFITS_SYSTEM_PROMPT), AIMessage(content=customer_benefits_prompt)]
    llm_with_structured_output = llm.with_structured_output(CustomerBenefits)
    ai_message = llm_with_structured_output.invoke(customer_benefits_messages)
    current_competitor.customer_benefits = ai_message.customer_benefits

    # Support benefits
    support_benefits_prompt = SUPPORT_BENEFITS_PROMPT.format(company_name=current_competitor.competitor_name, product_name=current_competitor.focus_product_or_service, product_text=str(current_competitor.documents))
    support_benefits_messages = [SystemMessage(content=SUPPORT_BENEFITS_SYSTEM_PROMPT), AIMessage(content=support_benefits_prompt)]
    llm_with_structured_output = llm.with_structured_output(SupportBenefits)
    ai_message = llm_with_structured_output.invoke(support_benefits_messages)
    current_competitor.support_benefits = ai_message.support_benefits

    # Usecases
    usecases_prompt = USECASES_PROMPT.format(company_name=current_competitor.competitor_name, product_name=current_competitor.focus_product_or_service, product_text=str(current_competitor.documents))
    usecases_messages = [SystemMessage(content=USECASES_SYSTEM_PROMPT), AIMessage(content=usecases_prompt)]
    llm_with_structured_output = llm.with_structured_output(Usecases)
    ai_message = llm_with_structured_output.invoke(usecases_messages)
    current_competitor.usecases = ai_message.usecases

    # Success benefits
    success_benefits_prompt = SUCCESS_BENEFITS_PROMPT.format(company_name=current_competitor.competitor_name, product_name=current_competitor.focus_product_or_service, product_text=str(current_competitor.documents))
    success_benefits_messages = [SystemMessage(content=SUCCESS_BENEFITS_SYSTEM_PROMPT), AIMessage(content=success_benefits_prompt)]
    llm_with_structured_output = llm.with_structured_output(SuccessBenefits)
    ai_message = llm_with_structured_output.invoke(success_benefits_messages)
    current_competitor.success_benefits = ai_message.success_benefits
    
    # Keywords
    keywords_prompt = KEYWORDS_PROMPT.format(company_name=current_competitor.competitor_name, product_name=current_competitor.focus_product_or_service, product_text=str(current_competitor.documents), keywords=current_competitor.keywords)
    keywords_messages = [SystemMessage(content=KEYWORDS_SYSTEM_PROMPT), AIMessage(content=keywords_prompt)]
    llm_with_structured_output = llm.with_structured_output(Keywords)
    ai_message = llm_with_structured_output.invoke(keywords_messages)
    current_competitor.keywords = ai_message.keywords



    return {"completed_competitors": [current_competitor]}

def synthesizer(state: WorkerState):
    """Synthesize full report from sections"""

    # List of completed sections
    completed_competitors = state["completed_competitors"]
    output = []
    final_report = ""
    for competitor in completed_competitors:
        temp_final_report = f"""
        {competitor.competitor_name}:
        {competitor.focus_product_or_service}
        Main idea:
        {competitor.main_idea_and_headline.main_idea}
        Headline:
        {competitor.main_idea_and_headline.headline}
        Value proposition:
        {competitor.value_proposition}
        Key customer benefits/Outcomes:
        {competitor.customer_benefits}
        Supporting benefits/capabilities:
        {competitor.support_benefits}
        Use cases:
        {competitor.usecases}
        Key stats/Proof/Customer stories:
        {competitor.success_benefits}
        Keywords:
        {competitor.keywords}
        """
        refine_prompt = "Please make the final report more concise and readable. Do not change the content of the report. if empty section remove it."
        refine_messages = [SystemMessage(content=refine_prompt), HumanMessage(content=temp_final_report)]
        ai_message = llm.invoke(refine_messages)
        llm_with_structured_output = llm.with_structured_output(CompetitorOutput)
        prompt = "please extract the following information from the following text: " + ai_message.content
        competitor_output = llm_with_structured_output.invoke(prompt)
        output.append(competitor_output)
        final_report += competitor_output.model_dump_json()
        final_report += "\n\n"

    return {"output": output, "final_report": final_report}

"""Graph"""
builder = StateGraph(CompetitiveAnalysisState)

"""Nodes"""
builder.add_node("user_questionnaire", user_questionnaire)
builder.add_node("orchestrate_competitive_analysis", orchestrate_competitive_analysis)
builder.add_node("competitive_analysis", competitive_analysis)
builder.add_node("synthesizer", synthesizer)
builder.add_edge(START, "user_questionnaire")

"""Conditional edges"""
builder.add_conditional_edges(
    "user_questionnaire",
    finish_questionnaire,
    {
        "continue_questions": "user_questionnaire",
        "finished": "orchestrate_competitive_analysis"
    }
)
builder.add_conditional_edges(
    "orchestrate_competitive_analysis",
    assign_workers,
    ["competitive_analysis"]
)

"""Edges"""
builder.add_edge("competitive_analysis", "synthesizer")
builder.add_edge("synthesizer", END)

CompetitiveAnalysisGraph = builder.compile()