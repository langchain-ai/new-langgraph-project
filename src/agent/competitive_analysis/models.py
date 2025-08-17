from pydantic import BaseModel
from typing import Optional
from typing_extensions import TypedDict
from typing import Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
import operator

"""Competitor analysis sections"""
class CustomerBenefits(BaseModel):
    customer_benefits: str

class SupportBenefits(BaseModel):
    support_benefits: str

class Usecases(BaseModel):
    usecases: str

class SuccessBenefits(BaseModel):
    success_benefits: str

class Keywords(BaseModel):
    keywords: str

class ValueProposition(BaseModel):
    value_proposition: str

class MainIdeaAndHeadline(BaseModel):
    main_idea: str
    headline: str

"""Competitor"""
class Competitor(BaseModel):
    competitor_name: str
    focus_product_or_service: str
    websites: list[str]
    documents: list[str]
    main_idea_and_headline: Optional[MainIdeaAndHeadline] = None
    value_proposition: Optional[ValueProposition] = None
    customer_benefits: Optional[CustomerBenefits] = None
    support_benefits: Optional[SupportBenefits] = None
    usecases: Optional[Usecases] = None
    success_benefits: Optional[SuccessBenefits] = None
    keywords: Optional[Keywords] = None

"""User questionnaire"""
class Answer(BaseModel):
    competitors_name: list[str]
    focus_product_or_service: str
    websites: list[str]

class PartialAnswers(BaseModel):
    competitors_name: Optional[list[str]] = None
    focus_product_or_service: Optional[str] = None
    websites: Optional[list[str]] = None

class QuestionResponse(BaseModel):
    extracted_answers: PartialAnswers
    still_need_answers_for: list[str] 
    next_message_with_question_and_greeting: Optional[str] = None
    conversation_complete: bool = False

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