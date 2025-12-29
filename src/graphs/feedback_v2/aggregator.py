from typing import Dict, Any, List
from .state import FeedbackState
from .schemas import AgentOutput

def aggregate_feedback(state: FeedbackState) -> FeedbackState:
    """Combines all agent outputs into a final, unified JSON report."""
    
    results: List[AgentOutput] = state["results"]
    
    # Calculate overall score or status
    failed_agents = [r.agent_name for r in results if r.status == "FAIL"]
    warnings = [r.agent_name for r in results if r.status == "WARNING"]
    
    final_status = "PASS"
    if failed_agents:
        final_status = "FAIL"
    elif warnings:
        final_status = "WARNING"

    # Structure the final report
    report = {
        "status": final_status,
        "summary": f"Passed: {len(results) - len(failed_agents) - len(warnings)}, Failed: {len(failed_agents)}, Warnings: {len(warnings)}",
        "details": [result.dict() for result in results]
    }
    
    state["aggregated_feedback"] = report
    return state
