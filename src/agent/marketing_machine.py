from typing import Annotated, Optional, Literal, TypedDict
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage, HumanMessage, AnyMessage
from langchain.chat_models import init_chat_model
from pydantic import BaseModel
from langgraph.types import interrupt, Command
from agent.messaging_framework import MessagingEngineSubgraph
from agent.competitive_analysis import CompetitiveAnalysisSubgraph
from agent.marketing_research import MarketingResearchSubgraph
from agent.content_engine import ContentEngineSubgraph

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


engine_list = ["MessagingEngine", "CompetitiveAnalysis", "MarketingResearch", "ContentEngine"]

# --------------------
# Prompt Definition
# --------------------
prompt = """
Classify the user’s input as one of:
- button (clicked a specific UI element)
- explicit (named a known engine from {engine_list})
- implicit (ambiguous need, choose the most likely engine from {engine_list})
- product_question (asking about WinScale or capabilities)
- irrelevant (off-topic)
- greeting (greeting the user, helping the user to explicitly state their need or click a button if they are not sure what they want)

Also suggest the most likely engine from {engine_list}, if applicable.

User input:
"{user_message}"

Respond as JSON:
  "routing_type": "...",
  "engine_suggestion": "..." (or null)
  "greeting_message": "..." (or null)
"""

class RoutingOutput(BaseModel):
    routing_type: Literal["button", "explicit", "implicit", "product_question", "irrelevant", "greeting"]
    engine_suggestion: Optional[Literal["MessagingEngine", "CompetitiveAnalysis", "MarketingResearch", "ContentEngine"]]
    greeting_message: Optional[str]


# --------------------
# Node Implementations
# --------------------
def classify_input(state: RouterState) -> RouterState:
    #last_user_msg = next((m.content for m in reversed(state["messages"]) if m.type == "human"), "")
    print("**********")
    prompt_with_user_message = prompt.format(engine_list=engine_list, user_message=state["messages"][-1].content)
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
        return {**state, "routing_type": llm_response.routing_type, "engine_suggestion": llm_response.engine_suggestion}

def direct_router(state: RouterState) -> RouterState:
    engine = state.get("engine_suggestion", "UnknownEngine")
    print(f"Routing directly to engine: {engine}")
    return state

def ask_for_confirmation(state: RouterState) -> RouterState:
    engine = state.get("engine_suggestion", "some engine")
    is_approved = interrupt(
    {
        "question": f"Just to confirm, do you want to proceed with {engine}?",
    }
    )
    print("********** Is Approved **********")
    print(is_approved)
    if is_approved:
        print("********** Approved **********")
        return Command(goto="DirectRouter")
    else:
        print("********** Not Approved **********")
        return Command(goto=START)


def answer_system_question(state: RouterState) -> RouterState:
    qa_prompt = """
    Sappington Winscale is an AI-powered sales and marketing platform designed to deliver a customer-customized experience at scale. It aims to transform B2B enterprise technology marketing by providing proactive, value-based, and automated solutions. Key components include the Command Center for real-time insights, the Marketing Machine for streamlined workflows and content creation, the Outcome Engine for identifying customer outcomes, and the Messaging Engine for differentiated messaging. The platform seeks to address current challenges of generic, product-focused, and slow marketing efforts by offering tailored content and faster delivery.
    User question:
    "{user_question}"

    Answer the question in a few sentences based on the information above. and ask gentle follow up questions if needed.
    """.format(user_question=state["messages"][-1].content[0]['text'])
    print("********** QA Prompt **********")
    print(qa_prompt)
    llm_response = llm.invoke(qa_prompt)
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
        "MessagingEngine": "MessagingEngine",
        "CompetitiveAnalysis": "CompetitiveAnalysis",
        "MarketingResearch": "MarketingResearch",
        "ContentEngine": "ContentEngine"
    }
)

builder.add_edge("AnswerSystemQuestion", END)
builder.add_edge("RejectIrrelevant", END)
builder.add_edge("DirectRouter", END)

graph = builder.compile()
