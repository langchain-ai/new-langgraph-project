from typing import List, Optional, Literal,Annotated, TypedDict
from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, AnyMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from langgraph.types import interrupt, Command

llm = init_chat_model(model="openai:gpt-4o")

QUESTIONS = [
    "Let's do some competitive analysis. Who are the competitors we want to analyze?",
    "What are the priorities of this competitive analysis?",
    "Focus on a product/service area or the entire company?",
    "Websites to include (optional, comma-separated):",
    "Specific keywords/terms (optional, comma-separated):",
    "Any special instructions? (optional)",
    "Reference materials (links; optional, comma-separated):",
]

class Answer(BaseModel):
    competitor_name: str
    priority : str
    focus_product_or_service: str
    websites: list[str] # optional
    keywords: list[str] # optional
    instructions: str # optional
    reference_materials: list[str] # optional

class next_question(BaseModel):
    question_with_greeting: str
    answered_all_questions: bool

class CompetitiveAnalysisState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    answers: Answer
    user_answered_all_questions: bool

system_prompt = f"""
You need to verify the user answer all the questions and if not, ask the next question. It is a part of a conversation so keep the greeting in your question.
The list of questions is:
{QUESTIONS}

Add to the first question you gonna ask this:
Welcome to the competitive analysis tool I'm going to ask you a few questions to help me understand your business and your competitors.

If the user answered you. say Thanks and blabla and ask the next question.

User the history of messages to verify if the user answered all the questions.

return True if the user answered all the questions, otherwise return False.
"""

def CompetitiveAnalysisNode(state: CompetitiveAnalysisState):
    system_message = SystemMessage(content=system_prompt)
    history = state['messages']
    messages = [system_message] + history
    
    llm_with_structured_output = llm.with_structured_output(next_question)
    ai_message = llm_with_structured_output.invoke(messages)
    
    if not ai_message.answered_all_questions:
        # Add the AI question to state before interrupting
        new_ai_message = AIMessage(content=ai_message.question_with_greeting)
        
        # Update state and interrupt
        user_response = interrupt({
            "question": ai_message.question_with_greeting,
        })
        
        # Return updated state with both AI question and human response
        # DON'T use Command(goto=...) - just update the state and let the conditional edge handle routing
        return {
            "messages": [new_ai_message, HumanMessage(content=user_response)],
            "user_answered_all_questions": False  # Explicitly set this
        }
    
    # All questions answered
    return {
        "messages": [AIMessage(content="Thanks! All questions completed.")],
        "user_answered_all_questions": True  # This will trigger the conditional edge
    }

system_prompt_fill_competitor_details = """
You need to fill the competitor details based on the user answers.
"""

def FillCompetitorDetails(state: CompetitiveAnalysisState):
    system_message = SystemMessage(content=system_prompt_fill_competitor_details)
    history = state['messages']
    messages = [system_message] + history

    llm_with_structured_output = llm.with_structured_output(Answer)
    ai_message = llm_with_structured_output.invoke(messages)

    return {
        "messages": [AIMessage(content=ai_message.competitor_name)],
        "user_answered_all_questions": True,
        "answers": ai_message
    }

# Conditional routing function
def should_continue(state: CompetitiveAnalysisState) -> Literal["continue_questions", "fill_details"]:
    if state.get("user_answered_all_questions", False):
        return "fill_details"
    else:
        return "continue_questions"

# Build the graph with conditional edges
builder = StateGraph(CompetitiveAnalysisState)

builder.add_node("CompetitiveAnalysisNode", CompetitiveAnalysisNode)
builder.add_node("FillCompetitorDetails", FillCompetitorDetails)

builder.add_edge(START, "CompetitiveAnalysisNode")

# Use conditional edge instead of fixed edge
builder.add_conditional_edges(
    "CompetitiveAnalysisNode",
    should_continue,
    {
        "continue_questions": "CompetitiveAnalysisNode",  # Loop back to ask more questions
        "fill_details": "FillCompetitorDetails"  # All questions answered, move to next step
    }
)

builder.add_edge("FillCompetitorDetails", END)

CompetitiveAnalysisSubgraph = builder.compile()