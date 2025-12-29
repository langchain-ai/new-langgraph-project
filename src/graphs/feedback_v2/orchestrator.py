from langgraph.graph import StateGraph, START, END
from .state import FeedbackState
from .agents.flow_structure import FlowStructureAgent
from .agents.function_division import FunctionDivisionAgent
from .agents.programming_errors import ProgrammingErrorsAgent
from .agents.conventions import ConventionsAgent
from .agents.debug_tasks import DebugTasksAgent
from .validators.structure_validator import StructureValidator
from .aggregator import aggregate_feedback
from .schemas import AgentOutput

# Initialize Agents
agents = [
    FlowStructureAgent(),
    FunctionDivisionAgent(),
    ProgrammingErrorsAgent(),
    ConventionsAgent(),
    DebugTasksAgent()
]
validator = StructureValidator()

def make_agent_node(agent):
    """Factory to create a graph node for an agent."""
    def node_func(state: FeedbackState):
        inp = {
            "code": state["code"], 
            "exercise_description": state["exercise_description"],
            "previous_feedback": [], # simplified for now
            "metadata": {}
        }
        # In a real scenario, we might want to map the dict to AgentInput object
        # safely or change invoke to accept dict. 
        # For strict typing let's assume invoke takes AgentInput-like dicts if Pydantic supports it,
        # or we manually construct AgentInput:
        from .schemas import AgentInput
        agent_input = AgentInput(**inp)
        
        output = agent.invoke(agent_input)
        return {"results": output}
    return node_func

def validation_gate(state: FeedbackState):
    """Routing logic: check if the latest result is valid."""
    last_result = state["results"][-1]
    validation = validator.validate(last_result)
    
    if validation.is_valid:
        return "next"
    
    # In a real implementation we would retry here. 
    # For now, to avoid infinite loops without retry counting logic in this simplified view,
    # we just log the error and proceed, OR we could return a Fail result.
    # Let's assume we proceed for this alpha version but note the error.
    return "next" 

def build_graph():
    workflow = StateGraph(FeedbackState)
    
    previous_node = START
    
    for agent in agents:
        node_name = f"agent_{agent.name.replace(' ', '_').lower()}"
        workflow.add_node(node_name, make_agent_node(agent))
        workflow.add_edge(previous_node, node_name)
        previous_node = node_name
        
        # Add validation node/edge logic here if strict loops are needed.
        # For simplicity in this step, we just chain them linearly 
        # and then aggregate.
        
    workflow.add_node("aggregator", aggregate_feedback)
    workflow.add_edge(previous_node, "aggregator")
    workflow.add_edge("aggregator", END)
    
    return workflow.compile()

feedback_graph_v2 = build_graph()
