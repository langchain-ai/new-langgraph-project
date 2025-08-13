from typing import List, Optional, Literal,Annotated, TypedDict
from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, AnyMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from langgraph.types import interrupt, Command
from langchain_core.documents import Document
from langchain_community.document_loaders import WebBaseLoader

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
    documents: Optional[list[Document]]
    main_idea: Optional[str]
    headline: Optional[str]
    value_proposition: Optional[str]
    aggregate_results: Optional[str]
    customer_benefits: Optional[str]
    support_benefits: Optional[str]
    usecases: Optional[str]
    success_benefits: Optional[str]
    keywords: Optional[str]


system_prompt = f"""
You need to verify the user answer all the questions and if not, ask the next question. It is a part of a conversation so keep the greeting in your question.
The list of questions is:
{QUESTIONS}

Instruction:
When starting the conversation, greet the user warmly and naturally. Briefly introduce that you’ll be conducting a competitive analysis and will ask a few quick questions to understand their business and competitors. Present the first question immediately after this introduction. Avoid any wording that suggests routing, transferring, or switching to another tool or agent — instead, make it feel like a single, continuous conversation with you.

After each user response, if the answer is clear and relevant, acknowledge it positively (e.g., “Thanks!” or “Got it, thank you”) and then ask the next question in the list. Maintain the same friendly, conversational tone throughout.

User the history of messages to verify if the user answered all the questions.

return True if the user answered all the questions, otherwise return False.
"""

def competitive_analysis_main(state: CompetitiveAnalysisState):
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

def fill_competitor_details(state: CompetitiveAnalysisState):
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

def fetch_documents(state: CompetitiveAnalysisState):
    
    loader = WebBaseLoader(state['answers'].websites)
    documents = loader.load()
    documents = [Document(page_content=document.page_content, metadata=document.metadata) for document in documents]
    #documents = await get_documents(state['answers'].websites)
    return {
        "documents": documents
    }

# Conditional routing function
def should_continue(state: CompetitiveAnalysisState) -> Literal["continue_questions", "fill_details"]:
    if state.get("user_answered_all_questions", False):
        return "fill_details"
    else:
        return "continue_questions"


def get_headline_with_llm(state: CompetitiveAnalysisState):
    headline_system_prompt = """
    You are a marketing analysit, your job is to only copy and paste text from a copmetitor website and EXTRACT EXACT TEXTS about the competing product and company. DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.

    You will be given a product texts from it's official webpage. You have several topics of texts to extract, now you woll only see one topic.
    You will read it and copy paste the exact text for the following topic.
    <topic_name>
    Top-level website review:
    Headline and main idea
    </topic_name>

    <topic_explanation>Capture the meain headline and the main idea that are present at the very top of the website, normally in the header.

    Headlines are short statements that set the context for the website or page, such as: “Do you have a firewall fit for today’s challenges?”

    Main ideas are typically brief sentences or statements that compliment the value proposition and the headline details, such as, “Analyze, act, and simplify with Secure Firewall.”

    Choose only one headline and one main idea.
    </topic_explanation>

    DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.

    Here is an example of an output:
    <example>
    Do you have a firewall to fit today's challenges?
    Anticipate, act, and simplify with Secure Firewall.
    </example>
    """
    headline_prompt = """
    Please EXTRACT COPY PASTE the text for the following without chaging the text product:

    <company_name>{{company_name}}</company_name>

    <product_name>{{product_name}}</product_name>

    <topic>Top-level website review:
    Taglines, headlines, and main ideas</topic>

    EXTRACT THE EXACT TEXT FROM THE FOLLOWING WEBSITE:
    <product_text>{{product_text}}</product_text>
    DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.
    """

    headline_prompt = headline_prompt.replace("{{company_name}}", state['answers'].competitor_name)
    headline_prompt = headline_prompt.replace("{{product_name}}", state['answers'].focus_product_or_service)
    headline_prompt = headline_prompt.replace("{{product_text}}", state['documents'][0].page_content)

    print(headline_prompt)

    class main_idea_and_headline(BaseModel):
        main_idea: str
        headline: str

    messages = [SystemMessage(content=headline_system_prompt), AIMessage(content=headline_prompt)]
    llm_with_structured_output = llm.with_structured_output(main_idea_and_headline)
    ai_message = llm_with_structured_output.invoke(messages)
    print(ai_message)
    return {
        "main_idea": ai_message.main_idea,
        "headline": ai_message.headline
    }

def get_value_proposition_with_llm(state: CompetitiveAnalysisState):
    value_system_prompt = """
    You are a marketing analysit, your job is to only copy and paste text from a copmetitor website and EXTRACT EXACT TEXTS about the competing product and company. DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.

    You will be given a product texts from it's official webpage. You have several topics of texts to extract, now you woll only see one topic.
    You will read it and copy paste the exact text for the following topic.
    <topic_name>
    Value proposition
    </topic_name>

    <topic_explanation>Locate and capture the value proposition, typically a sentence following the tagline or main idea above the fold. Value proposition connects customers needs with the vendor’s solution in a differentiated way.

    An example is, “Protect your network with Quantum gateways, the most effective AI-powered firewalls, featuring the highest rated threat prevention, seamless scalability, and unified policy management.”
    </topic_explanation>

    DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.

    Here is an example of an output:
    <example>
    FortiGate provides flawless convergence that can scale to any location: remote office, branch, campus, data center, and cloud. We’ve always delivered on the concept of hybrid mesh firewalls with FortiManager for unified management and consistent security across complex hybrid environments. The Fortinet FortiOS operating system provides deep visibility and security across a variety of form factors.
    FortiGate NGFW is the world’s most deployed network firewall, delivering unparalleled AI-powered security performance and threat intelligence, along with full visibility and security and networking convergence.
    </example>
    """
    value_prompt = """
    Please EXTRACT COPY PASTE the text for the following without chaging the text product:

    <company_name>{{company_name}}</company_name>

    <product_name>{{product_name}}</product_name>

    <topic>Value proposition</topic>

    EXTRACT THE EXACT TEXT FROM THE FOLLOWING WEBSITE:
    <product_text>{{product_text}}</product_text>
    DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.
    """

    value_prompt = value_prompt.replace("{{company_name}}", state['answers'].competitor_name)
    value_prompt = value_prompt.replace("{{product_name}}", state['answers'].focus_product_or_service)
    value_prompt = value_prompt.replace("{{product_text}}", state['documents'][0].page_content)

    print(value_prompt)

    class value_proposition(BaseModel):
        value_proposition: str

    messages = [SystemMessage(content=value_system_prompt), AIMessage(content=value_prompt)]
    llm_with_structured_output = llm.with_structured_output(value_proposition)
    ai_message = llm_with_structured_output.invoke(messages)
    print(ai_message)
    return {
        "value_proposition": ai_message.value_proposition
    }

def get_customer_benefits_with_llm(state: CompetitiveAnalysisState):
    customer_benefits_system_prompt = """
    You are a marketing analysit, your job is to only copy and paste text from a copmetitor website and EXTRACT EXACT TEXTS about the competing product and company. DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.

    You will be given a product texts from it's official webpage. You have several topics of texts to extract, now you woll only see one topic.
    You will read it and copy paste the exact text for the following topic.
    <topic_name>
    Customer benefits
    </topic_name>

    <topic_explanation>Typically, a website will have the key customer benefits (typically three) displayed in prominence. A customer benefit can be a word, or a brief phrase (e.g., “Convergence”, “Achieve superior visibility”), followed by a sentence further describing the customer benefit.

    Example:

    “Block the most evasive threats automatically

    Our firewalls have the highest security rating with a 99.8% block rate against zero day attacks, leveraging 50+ AI engines and real-time global threat intelligence”
    </topic_explanation>

    DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.

    Here is an example of an output:
    <example>
    Convergence: One operating system provides unified networking and security across all form factors and edges.
    Acceleration: Patented ASIC architecture for improved performance, greater ROI, and reduced power consumption.
    AI/ML Security: FortiGuard global threat intelligence delivers automated protection against known & unknown threats .
    </example>
    """
    customer_benefits_prompt = """
    Please EXTRACT COPY PASTE the text for the following without chaging the text product:

    <company_name>{{company_name}}</company_name>

    <product_name>{{product_name}}</product_name>

    <topic>Customer benefits</topic>

    EXTRACT THE EXACT TEXT FROM THE FOLLOWING WEBSITE:
    <product_text>{{product_text}}</product_text>
    DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.
    """

    customer_benefits_prompt = customer_benefits_prompt.replace("{{company_name}}", state['answers'].competitor_name)
    customer_benefits_prompt = customer_benefits_prompt.replace("{{product_name}}", state['answers'].focus_product_or_service)
    customer_benefits_prompt = customer_benefits_prompt.replace("{{product_text}}", state['documents'][0].page_content)

    print(customer_benefits_prompt)

    class customer_benefits(BaseModel):
        customer_benefits: str

    messages = [SystemMessage(content=customer_benefits_system_prompt), AIMessage(content=customer_benefits_prompt)]
    llm_with_structured_output = llm.with_structured_output(customer_benefits)
    ai_message = llm_with_structured_output.invoke(messages)
    print(ai_message)

    return {
        "customer_benefits": ai_message.customer_benefits
    }

def get_support_benefits_with_llm(state: CompetitiveAnalysisState):
    support_benefits_system_prompt = """
    You are a marketing analysit, your job is to only copy and paste text from a copmetitor website and EXTRACT EXACT TEXTS about the competing product and company. DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.

    You will be given a product texts from it's official webpage. You have several topics of texts to extract, now you woll only see one topic.
    You will read it and copy paste the exact text for the following topic.
    <topic_name>
    Support benefits or capabilities
    </topic_name>

    <topic_explanation>Normally, beneath the customer benefits include support benefits or capabilities for those main benefits. Often, these supporting details will provide more product-level benefits.

    Examples:

    Optimal performance and highest rated security for the most demanding networks and data centers
    Automatic, real-time threat intelligence enables firewalls to proactively detect and block attacks
    Advanced threat prevention ranging from 450 Mbps to 1 Tbps of network throughput
    Flexible modularity for dynamic network interface requirements
    Unified policy management for on-prem and cloud firewalls
    Easy integration with 3rd party SOC and automation systems via comprehensive APIs
    </topic_explanation>

    DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.

    Here is an example of an output:
    <example>
    FortiGuard AI-powered Security Bundles for FortiGate: Powerful security and support services elevate FortiGate NGFW and Fortinet NGFW-based solutions
    FortiGuard AI-powered security bundles provide a comprehensive and meticulously curated selection of security services to combat known, unknown, zero-day, and emerging AI-based threats. These services are designed to prevent malicious content from breaching your defenses, protect against web-based threats, secure devices throughout IT/OT/IoT environments, and ensure the safety of applications, users, and data.
    Advanced Threat Protection
    Unified Threat Protection
    Enterprise Protection
    </example>
    """

    support_benefits_prompt = """
    Please EXTRACT COPY PASTE the text for the following without chaging the text product:

    <company_name>{{company_name}}</company_name>

    <product_name>{{product_name}}</product_name>

    <topic>Support benefits or capabilities</topic>

    EXTRACT THE EXACT TEXT FROM THE FOLLOWING WEBSITE:
    <product_text>{{product_text}}</product_text>
    DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.
    """

    support_benefits_prompt = support_benefits_prompt.replace("{{company_name}}", state['answers'].competitor_name)
    support_benefits_prompt = support_benefits_prompt.replace("{{product_name}}", state['answers'].focus_product_or_service)
    support_benefits_prompt = support_benefits_prompt.replace("{{product_text}}", state['documents'][0].page_content)

    print(support_benefits_prompt)

    class support_benefits(BaseModel):
        support_benefits: str

    messages = [SystemMessage(content=support_benefits_system_prompt), AIMessage(content=support_benefits_prompt)]
    llm_with_structured_output = llm.with_structured_output(support_benefits)
    ai_message = llm_with_structured_output.invoke(messages)
    print(ai_message)

    return {
        "support_benefits": ai_message.support_benefits
    }

def get_usecases_with_llm(state: CompetitiveAnalysisState):
    usecases_system_prompt = """
    You are a marketing analysit, your job is to only copy and paste text from a copmetitor website and EXTRACT EXACT TEXTS about the competing product and company. DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.

    You will be given a product texts from it's official webpage. You have several topics of texts to extract, now you woll only see one topic.
    You will read it and copy paste the exact text for the following topic.
    <topic_name>
    Use Cases
    </topic_name>

    <topic_explanation>In addition to customer benefits and supporting details, companies may also include relevant use cases (e.g., Marketing automation, hybrid work).

    Example, “Secure enterprise branch office networks”
    </topic_explanation>

    DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.

    Here is an example of an output:
    <example>
    Replace MPLS/Increase bandwidth
    Global connectivity
    Secure DIA
    Optimize cloud access
    Optimize mobile access
    Simplify management
    </example>
    """

    usecases_benefits_prompt = """
    Please EXTRACT COPY PASTE the text for the following without chaging the text product:

    <company_name>{{company_name}}</company_name>

    <product_name>{{product_name}}</product_name>

    <topic>Use Cases</topic>

    EXTRACT THE EXACT TEXT FROM THE FOLLOWING WEBSITE:
    <product_text>{{product_text}}</product_text>
    DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.
    IF NO USE CASE PRESENT RETURN NONE
    """

    usecases_benefits_prompt = usecases_benefits_prompt.replace("{{company_name}}", state['answers'].competitor_name)
    usecases_benefits_prompt = usecases_benefits_prompt.replace("{{product_name}}", state['answers'].focus_product_or_service)
    usecases_benefits_prompt = usecases_benefits_prompt.replace("{{product_text}}", state['documents'][0].page_content)

    print(usecases_benefits_prompt)

    class usecases(BaseModel):
        usecases: str

    messages = [SystemMessage(content=usecases_system_prompt), AIMessage(content=usecases_benefits_prompt)]
    llm_with_structured_output = llm.with_structured_output(usecases)
    ai_message = llm_with_structured_output.invoke(messages)
    print(ai_message)

    return {
        "usecases": ai_message.usecases
    }

def get_success_with_llm(state: CompetitiveAnalysisState):
    success_system_prompt = """
    You are a marketing analysit, your job is to only copy and paste text from a copmetitor website and EXTRACT EXACT TEXTS about the competing product and company. DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.

    You will be given a product texts from it's official webpage. You have several topics of texts to extract, now you woll only see one topic.
    You will read it and copy paste the exact text for the following topic.
    <topic_name>
    Stats, third-party validation, customer success
    </topic_name>

    <topic_explanation>Capture any provided stats (e.g., #1 deployed firewall), third-party validation (e.g., Gartner Magic Quadrant, Forrester Wave, etc.), names of customers, and a summary sentence of the customer success detail.

    Example:

    Third party validation: “Check Point Named NGFW Firewall Company of the Year – Frost & Sullivan”

    Customer case study: “Ampol's global business includes refineries, fueling stations, and corporate offices. The company's infrastructure and retail operations are protected and connected with Cisco technology.”
    </topic_explanation>

    DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.

    Here is an example of an output:
    <example>
    “By 2026, More than 60% of Organizations Will Have One or More Firewall Deployments”
    Fortinet Named a Leader in the 2022 Gartner® Magic Quadrant™ for Network Firewalls
    Fortinet Achieves a 99.88% Security Effectiveness Score in the CyberRatings 2023 Enterprise Firewall Report
    Forrester Total Economic Impact™ (TEI)study: Fortinet NGFW for Data Center And AI-Powered FortiGuard Security Services
    Forrester Total Economic Impact™ (TEI) study reveals 318% ROI and $10.6M in cost benefits achieved with the Fortinet Data Center cybersecurity solution.
    Fortinet Named a Leader in The Forrester Wave™: Enterprise Firewalls, Q4 2022
    Grupo Morsa
    Grey County
    Capital Energy
    </example>
    """

    success_benefits_prompt = """
    Please EXTRACT COPY PASTE the text for the following without chaging the text product:

    <company_name>{{company_name}}</company_name>

    <product_name>{{product_name}}</product_name>

    <topic>Stats, third-party validation, customer success</topic>

    EXTRACT THE EXACT TEXT FROM THE FOLLOWING WEBSITE:
    <product_text>{{product_text}}</product_text>
    DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.
    IF NO USE CASE PRESENT RETURN NONE
    """

    success_benefits_prompt = success_benefits_prompt.replace("{{company_name}}", state['answers'].competitor_name)
    success_benefits_prompt = success_benefits_prompt.replace("{{product_name}}", state['answers'].focus_product_or_service)
    success_benefits_prompt = success_benefits_prompt.replace("{{product_text}}", state['documents'][0].page_content)

    print(success_benefits_prompt)

    class success_benefits(BaseModel):
        success_benefits: str

    messages = [SystemMessage(content=success_system_prompt), AIMessage(content=success_benefits_prompt)]
    llm_with_structured_output = llm.with_structured_output(success_benefits)
    ai_message = llm_with_structured_output.invoke(messages)
    print(ai_message)

    return {
        "success_benefits": ai_message.success_benefits
    }

def get_keywords_with_llm(state: CompetitiveAnalysisState):
    keywords_system_prompt = """
    You are a marketing analysit, your job is to only copy and paste text from a copmetitor website and EXTRACT EXACT TEXTS about the competing product and company. DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.

    You will be given a product texts from it's official webpage. You have several topics of texts to extract, now you woll only see one topic.
    You will read it and copy paste the exact text for the following topic.
    <topic_name>
    Keywords
    </topic_name>

    <topic_explanation>
    We include specific keywords that they want to see if other competitors are also using, and how they are using. We will need a list of keywords as input from the user to include in the analysis. Example keywords are “AI,” “unification,” and “simplicity.

    Based on user keyword input, search across the competitors’ websites to determine if they are using that keyword, and how they are using those keywords.

    List specific usage of keywords in the output.
    If they are not using it return none as a bullet point

    Also, identify if there are adjacent keywords that are being used. For example, if “AI” is a keyword, find and include any derivatives, such as, “AI-powered” or “AI-enabled” in the output.
    </topic_explanation>

    DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.
    <example>
    Zero Trust
    - Netskope Next Gen SASE Branch converges Context-Aware SASE Fabric, Zero-Trust Hybrid Security, and SkopeAI-powered Cloud Orchestrator into a unified cloud offering
    - Learn about Zero Trust
    - Zero trust solutions for SSE and SASE deployments

    Simplify
    - Netskope delivers a complete range of single-vendor SASE capabilities tailored for various customer sizes and technology environments, ranging from midmarket businesses to large enterprises. In line with the security and connectivity outcomes prescribed in the SASE framework, Netskope One SASE provides AI-driven zero trust security and simplified, optimized connectivity to any network location or device, including IoT.
    - The strength of Netskope, for us, is the way it simplifies our architecture. We no longer need anything on-premise, we have a single point of access, a single client, and integrated threat and data protection.
    </example>
    """

    keywords_prompt = """
    Please EXTRACT COPY PASTE the text for the following without chaging the text product:

    <company_name>{{company_name}}</company_name>

    <product_name>{{product_name}}</product_name>

    <topic>Keywords</topic>

    <keywords>{{keywords}}</keywords>

    EXTRACT THE EXACT TEXT FROM THE FOLLOWING WEBSITE:
    <product_text>{{product_text}}</product_text>
    DO NOT EDIT THE TEXT OR SUMMARIZE IT JUST COPY PASTE.
    IF NO USE CASE PRESENT RETURN NONE
    """

    keywords_prompt = keywords_prompt.replace("{{company_name}}", state['answers'].competitor_name)
    keywords_prompt = keywords_prompt.replace("{{product_name}}", state['answers'].focus_product_or_service)
    keywords_prompt = keywords_prompt.replace("{{product_text}}", state['documents'][0].page_content)
    keywords_prompt = keywords_prompt.replace("{{keywords}}", ", ".join(state['answers'].keywords))

    print(keywords_prompt)

    class keywords(BaseModel):
        keywords: str

    messages = [SystemMessage(content=keywords_system_prompt), AIMessage(content=keywords_prompt)]
    llm_with_structured_output = llm.with_structured_output(keywords)
    ai_message = llm_with_structured_output.invoke(messages)
    print(ai_message)

    return {
        "keywords": ai_message.keywords
    }

def aggregate_results(state: CompetitiveAnalysisState):
    aggregate_results = f"""Main ideas/Headlines:
        {state['main_idea']}
        {state['headline']}

        Value proposition
        {state['value_proposition']}

        Key customer benefits/Outcomes
        {state['customer_benefits']}

        Supporting benefits/capabilities
        {state['support_benefits']}

        Use cases
        {state['usecases']}

        Key stats/Proof/Customer stories
        {state['success_benefits']}

        Keywords
        {state['keywords']}
        """
    
    return {
        "aggregate_results": aggregate_results,
        "messages": aggregate_results
    }

# Build the graph with conditional edges
builder = StateGraph(CompetitiveAnalysisState)

builder.add_node("CompetitiveAnalysisNode", competitive_analysis_main)
builder.add_node("FillCompetitorDetails", fill_competitor_details)
builder.add_node("FetchDocuments", fetch_documents)
builder.add_node("GetHeadline", get_headline_with_llm)
builder.add_node("GetValueProposition", get_value_proposition_with_llm)
builder.add_node("GetCustomerBenefits", get_customer_benefits_with_llm)
builder.add_node("GetSupportBenefits", get_support_benefits_with_llm)
builder.add_node("GetUsecases", get_usecases_with_llm)
builder.add_node("GetSuccessBenefits", get_success_with_llm)
builder.add_node("GetKeywords", get_keywords_with_llm)
builder.add_node("AggregateResults", aggregate_results)

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

builder.add_edge("FillCompetitorDetails", "FetchDocuments")
builder.add_edge("FetchDocuments", "GetHeadline")
builder.add_edge("FetchDocuments", "GetCustomerBenefits")
builder.add_edge("FetchDocuments", "GetValueProposition")
builder.add_edge("FetchDocuments", "GetSupportBenefits")
builder.add_edge("FetchDocuments", "GetUsecases")
builder.add_edge("FetchDocuments", "GetSuccessBenefits")
builder.add_edge("FetchDocuments", "GetKeywords")
builder.add_edge("GetHeadline", "AggregateResults")
builder.add_edge("GetValueProposition", "AggregateResults")
builder.add_edge("GetCustomerBenefits", "AggregateResults")
builder.add_edge("GetSupportBenefits", "AggregateResults")
builder.add_edge("GetUsecases", "AggregateResults")
builder.add_edge("GetKeywords", "AggregateResults")
builder.add_edge("GetSuccessBenefits", "AggregateResults")
builder.add_edge("AggregateResults", END)

CompetitiveAnalysisSubgraph = builder.compile()