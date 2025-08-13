from typing import List, Optional, Literal,Annotated
from typing_extensions import TypedDict
from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, AnyMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langchain.chat_models import init_chat_model
from langgraph.types import interrupt, Command
from langchain_core.documents import Document
from langchain_community.document_loaders import WebBaseLoader
from tavily import TavilyClient
from operator import add
import os


llm = init_chat_model(model="openai:gpt-4o")
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))




QUESTIONS = [
    "Let's do some competitive analysis. Who are the competitors we want to analyze?",
    #"What are the priorities of this competitive analysis?",
    "Focus on a product/service area or the entire company?",
    "Websites to include (optional, comma-separated):",
    "Specific keywords/terms (optional, comma-separated):",
    "Any special instructions? (optional)",
    "Reference materials (links; optional, comma-separated):",
]

class Answer(BaseModel):
    competitor_name: str
    focus_product_or_service: str
    websites: list[str] # optional
    keywords: list[str] # optional
    instructions: str # optional
    reference_materials: list[str] # optional

class PartialAnswers(BaseModel):
    competitor_name: Optional[str] = None
    focus_product_or_service: Optional[str] = None
    websites: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    instructions: Optional[str] = None
    reference_materials: Optional[list[str]] = None

class QuestionResponse(BaseModel):
    extracted_answers: PartialAnswers
    still_need_answers_for: list[str]  # List of field names still needed
    next_message_with_question_and_greeting: Optional[str] = None
    conversation_complete: bool = False

class CompetitiveAnalysisState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    answers: Answer
    user_answered_all_questions: bool
    documents: Optional[Annotated[list[str], add]]
    main_idea: Optional[str]
    headline: Optional[str]
    value_proposition: Optional[str]
    aggregate_results: Optional[str]
    customer_benefits: Optional[str]
    support_benefits: Optional[str]
    usecases: Optional[str]
    success_benefits: Optional[str]
    keywords: Optional[str]


# Updated system prompt
system_prompt = f"""
You are conducting a competitive analysis interview. Extract any relevant information from the user's response that answers any of these questions:

{QUESTIONS}

From the user's message, extract any information that corresponds to:
- competitor_name: The name of the competitor
- focus_product_or_service: Main product/service focus
- websites: Any website URLs mentioned
- keywords: Relevant keywords or search terms
- instructions: Special instructions or notes
- reference_materials: Documents, links, or materials referenced

Based on what you've extracted and the conversation history, determine:
1. What information is still missing
2. What the next logical question should be
3. Whether the conversation is complete

Be conversational and acknowledge what the user provided before asking for missing information.

Important:
- Based on the previous message, be greeting and friendly and make it conversational.
- Add the greeting to the beginning of the message.
"""

def competitive_analysis_main(state: CompetitiveAnalysisState):
    system_message = SystemMessage(content=system_prompt)
    history = state['messages']
    messages = [system_message] + history
    
    llm_with_structured_output = llm.with_structured_output(QuestionResponse)
    response = llm_with_structured_output.invoke(messages)
    
    # Update the answers with extracted information
    current_answers = state.get('answers', Answer(
        competitor_name="", focus_product_or_service="",
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

system_prompt_fill_competitor_details = """
You need to fill the competitor details based on the user answers.
"""

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

def route_to_documents_source(state: CompetitiveAnalysisState):
    if state['answers'].websites:
        return "fetch_documents"
    else:
        return "web_search"

def web_search(state: CompetitiveAnalysisState):
    query = f"{state['answers'].competitor_name} {state['answers'].focus_product_or_service}"

    response = tavily_client.search(
        query=query
    )
    
    documents = [Document(page_content=result['content'], metadata=result) for result in response['results']]

    return {
        "documents": documents
    }

def fetch_documents(state: CompetitiveAnalysisState):
    
    loader = WebBaseLoader(state['answers'].websites)
    documents = loader.load()
    documents = [Document(page_content=document.page_content, metadata=document.metadata) for document in documents]

    return {
        "documents": documents
    }

# Conditional routing function
def should_continue_and_route(state: CompetitiveAnalysisState) -> Literal["continue_questions", "fetch_documents", "web_search"]:
    if not state.get("user_answered_all_questions", False):
        return "continue_questions"
    elif state['answers'].websites:
        return "fetch_documents" 
    else:
        return "web_search"

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
    aggregate_results_message = AIMessage(content=aggregate_results)
    return {
        "aggregate_results": aggregate_results,
        "messages": [aggregate_results_message]
    }

# Build the graph with conditional edges
builder = StateGraph(CompetitiveAnalysisState)

builder.add_node("CompetitiveAnalysisNode", competitive_analysis_main)
#אני builder.add_node("FillCompetitorDetails", fill_competitor_details)
builder.add_node("FetchDocuments", fetch_documents)
builder.add_node("WebSearch", web_search)
builder.add_node("GetHeadline", get_headline_with_llm)
builder.add_node("GetValueProposition", get_value_proposition_with_llm)
builder.add_node("GetCustomerBenefits", get_customer_benefits_with_llm)
builder.add_node("GetSupportBenefits", get_support_benefits_with_llm)
builder.add_node("GetUsecases", get_usecases_with_llm)
builder.add_node("GetSuccessBenefits", get_success_with_llm)
builder.add_node("GetKeywords", get_keywords_with_llm)
builder.add_node("AggregateResults", aggregate_results)

builder.add_edge(START, "CompetitiveAnalysisNode")


builder.add_conditional_edges(
    "CompetitiveAnalysisNode",
    should_continue_and_route,
    {
        "continue_questions": "CompetitiveAnalysisNode",
        "fetch_documents": "FetchDocuments",
        "web_search": "WebSearch" 
    }
)

builder.add_edge("WebSearch", "GetHeadline")
builder.add_edge("WebSearch", "GetCustomerBenefits")
builder.add_edge("WebSearch", "GetValueProposition")
builder.add_edge("WebSearch", "GetSupportBenefits")
builder.add_edge("WebSearch", "GetUsecases")
builder.add_edge("WebSearch", "GetSuccessBenefits")
builder.add_edge("WebSearch", "GetKeywords")
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