from dotenv import load_dotenv
import os
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda

# ✅ Load environment
load_dotenv()

# ✅ DEBUG print to confirm key is loaded
print("OPENAI_KEY LOADED:", os.getenv("OPENAI_API_KEY")[:10], "...")
print("LangSmith project:", os.getenv("LANGSMITH_PROJECT"))

# ✅ Reusable LLM
llm = ChatOpenAI(model="gpt-4", temperature=0)

# 🧠 Node: Supervisor (decides flow, stubbed for now)
def supervisor_node(state: dict) -> dict:
    print("🧭 Supervisor: Deciding flow...")
    return {"form_type": "accident_report"}

# 🧠 Node: Form Selector (uses LLM to describe form)
def form_selector_node(state: dict) -> dict:
    form_type = state.get("form_type", "unknown")
    print(f"📄 Form Selector: Received form type → {form_type}")
    message = f"You are helping complete a form of type: {form_type}. What's the first field?"
    response = llm.invoke(message)
    return {"form_type": form_type, "first_field": response.content}

# 🧠 Node: Form Completion (mock interaction)
def form_completion_node(state: dict) -> dict:
    print(f"✍️ Form Completion: Starting with → {state.get('first_field')}")
    response = llm.invoke("Let's pretend to fill out this form together.")
    return {"form_complete": response.content}

# 🧠 Node: Validator (trivial check for now)
def validator_node(state: dict) -> dict:
    print("✅ Validator: Verifying...")
    is_valid = "form_complete" in state
    return {"valid": is_valid}

# ✅ Build the LangGraph DAG
from typing import TypedDict, Optional

class GraphState(TypedDict, total=False):
    input: Optional[str]
    form_type: Optional[str]
    first_field: Optional[str]
    form_complete: Optional[str]
    valid: Optional[bool]

graph = StateGraph(GraphState)


graph.add_node("supervisor", RunnableLambda(supervisor_node))
graph.add_node("form_selector", RunnableLambda(form_selector_node))
graph.add_node("form_completion", RunnableLambda(form_completion_node))
graph.add_node("validator", RunnableLambda(validator_node))

# ⛓️ Wire nodes together
graph.set_entry_point("supervisor")
graph.add_edge("supervisor", "form_selector")
graph.add_edge("form_selector", "form_completion")
graph.add_edge("form_completion", "validator")
graph.add_edge("validator", END)

# ✅ Compile and Run
dag = graph.compile()

# 🧪 Invoke with empty state
print("\n🧪 Running VoicedForm DAG...\n")
output = dag.invoke({})
print("\n🎉 Final output:", output)
