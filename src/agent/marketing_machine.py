from typing import Annotated, Optional, Literal, TypedDict
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, HumanMessage, AnyMessage
from langchain.chat_models import init_chat_model
from pydantic import BaseModel
from langgraph.types import interrupt, Command
from agent.messaging_framework import MessagingEngineSubgraph
from agent.competitive_analysis.competitive_analysis import CompetitiveAnalysisGraph as CompetitiveAnalysisSubgraph
from agent.marketing_research import MarketingResearchSubgraph
from agent.content_engine import ContentEngineSubgraph
from agent.PROMPTS import QuestionAnsweringPrompt, QuestionAnsweringContext, ImplicitRoutingContext, ClassifyInputPrompt

# --------------------
# LLM Definition
# --------------------
llm = init_chat_model(model="openai:gpt-4o")



# --------------------
# State Definition 
# --------------------
class RouterState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    routing_type: Optional[Literal["button", "explicit", "implicit", "product_question", "irrelevant", "greeting"]]
    engine_suggestion: Optional[str]
    confirmation_given: Optional[bool]
    confirmation_message_for_implicit: Optional[str]


engine_list = ["Messaging Framework", "Competitive Analysis", "Marketing Research", "Content Engine", "Messaging Engine"]

# --------------------
# Structured Output Definition
# --------------------

class ApprovalResponse(BaseModel):
    approved: bool
    follow_up_message: Optional[str] = None


class RoutingOutput(BaseModel):
    routing_type: Literal["button", "explicit", "implicit", "product_question", "irrelevant", "greeting"]
    engine_suggestion: Optional[Literal["Messaging Framework", "Competitive Analysis", "Marketing Research", "Content Engine", "Messaging Engine"]]
    greeting_message: Optional[str]
    confirmation_message_for_implicit: Optional[str]


# --------------------
# Node Implementations
# --------------------
def classify_input(state: RouterState) -> RouterState:
    #last_user_msg = next((m.content for m in reversed(state["messages"]) if m.type == "human"), "")
    print("**********")
    
    # Get conversation context (exclude the current message)
    if len(state["messages"]) > 1:
        # Get the last 2-3 messages before the current one
        context_messages = state["messages"][-3:-1] if len(state["messages"]) >= 3 else state["messages"][:-1]
        context_text = "\n".join([f"{msg.type}: {msg.content}" for msg in context_messages])
        context_section = f"Previous conversation context:\n{context_text}\n"
    else:
        context_section = ""

    prompt_with_user_message = ClassifyInputPrompt.format(
        engine_list=engine_list,
        user_message=state["messages"][-1].content,
        examples=ImplicitRoutingContext,
        context_section=context_section
    )
    print("********** Prompt with User Message **********")
    print(prompt_with_user_message)
    llm_with_schema = llm.with_structured_output(schema=RoutingOutput)
    llm_response = llm_with_schema.invoke(prompt_with_user_message)
    print("********** LLM Response **********")
    print(llm_response)
    if llm_response.routing_type == "greeting":
        print("********** Greeting **********")
        return {**state, "routing_type": llm_response.routing_type, "messages": AIMessage(content=llm_response.greeting_message) }
    else:
        print("********** Not Greeting **********")
        return {**state, "routing_type": llm_response.routing_type, "engine_suggestion": llm_response.engine_suggestion, "confirmation_message_for_implicit": llm_response.confirmation_message_for_implicit}

def direct_router(state: RouterState) -> RouterState:
    engine = state.get("engine_suggestion", "UnknownEngine")
    print(f"Routing directly to engine: {engine}")
    return state

def ask_for_confirmation(state: RouterState) -> RouterState:
    engine = state.get("engine_suggestion", "some engine")
    user_confirmation_message = state.get("confirmation_message_for_implicit", f"Just to confirm, do you want to proceed with {engine}?")
    print("********** User Confirmation Message **********")
    print(user_confirmation_message)
    
    # Get user response
    user_response = interrupt({
        "question": user_confirmation_message,
    })
    print("********** User Response **********")
    print(user_response)
    
    # Use LLM to process the approval with structured output
    last_messages = state["messages"][-2:] if len(state["messages"]) >= 2 else state["messages"]
    context_messages = "\n".join([f"{msg.type}: {msg.content}" for msg in last_messages])
    
    approval_prompt = f"""
    Analyze the user's response to determine if they approved the routing suggestion.
    
    Previous conversation context:
    {context_messages}
    
    User's response: "{user_response}"
    
    Return:
    - approved: true if the user said yes/agreed/approved, false otherwise
    - follow_up_message: if not approved, provide a helpful message asking what they'd like to do instead
    """
    
    llm_with_approval_schema = llm.with_structured_output(schema=ApprovalResponse)
    approval_result = llm_with_approval_schema.invoke(approval_prompt)
    
    print("********** Approval Result **********")
    print(approval_result)
    
    if approval_result.approved:
        print("********** Approved **********")
        # Add user's approval to the conversation history
        updated_state = {
            **state, 
            "messages": state["messages"] + [HumanMessage(content=user_response)]
        }
        return Command(goto="DirectRouter", update=updated_state)
    else:
        print("********** Not Approved **********")
        follow_up = approval_result.follow_up_message or "I understand you'd like to do something different. What would you like to accomplish today?"
        return {
            **state, 
            "messages": state["messages"] + [
                HumanMessage(content=user_response),
                AIMessage(content=follow_up)
            ]
        }

def answer_system_question(state: RouterState) -> RouterState:
    #qa_prompt = QuestionAnsweringPrompt.format(question=state["messages"][-1].content[0]['text'])
    user_question = state["messages"][-1].content
    qna_prompt = QuestionAnsweringPrompt.format(context=QuestionAnsweringContext, question=user_question)
    print("********** QA Prompt **********")
    print(user_question)
    print(qna_prompt)
    llm_response = llm.invoke(qna_prompt)
    print("********** QA LLM Response **********")
    print(llm_response)
    state["messages"].append(AIMessage(content=llm_response.content))
    return state

def reject_irrelevant(state: RouterState) -> RouterState:
    state["messages"].append(AIMessage(content="Sorry, I can't help with that. Please tell me what you want to do today, click a button to get started, or ask a relevant question to get started."))
    return state

# --------------------
# Graph Definition
# --------------------
builder = StateGraph(RouterState)
builder.add_node("ClassifyInput", classify_input)
builder.add_node("DirectRouter", direct_router)
builder.add_node("UserConfirmation", ask_for_confirmation)
builder.add_node("AnswerSystemQuestion", answer_system_question)
builder.add_node("RejectIrrelevant", reject_irrelevant)

# --------------------
# Subgraphs
# --------------------
builder.add_node("MessagingEngine", MessagingEngineSubgraph)
builder.add_node("CompetitiveAnalysis", CompetitiveAnalysisSubgraph)
builder.add_node("MarketingResearch", MarketingResearchSubgraph)
builder.add_node("ContentEngine", ContentEngineSubgraph)

# Edges
builder.set_entry_point("ClassifyInput")

builder.add_conditional_edges(
    "ClassifyInput",
    lambda state: state["routing_type"],
    {
        "button": "DirectRouter",
        "explicit": "DirectRouter",
        "implicit": "UserConfirmation",
        "product_question": "AnswerSystemQuestion",
        "irrelevant": "RejectIrrelevant",
        "greeting": END
    },
)

builder.add_conditional_edges(
    "DirectRouter",
    lambda state: state["engine_suggestion"],
    {
        "Messaging Framework": "MessagingEngine",
        "Competitive Analysis": "CompetitiveAnalysis",
        "Marketing Research": "MarketingResearch",
        "Content Engine": "ContentEngine",
        "Messaging Engine": "MessagingEngine"
    }
)

builder.add_edge("AnswerSystemQuestion", END)
builder.add_edge("RejectIrrelevant", END)
builder.add_edge("DirectRouter", END)
builder.add_edge("UserConfirmation", END)

graph = builder.compile()
