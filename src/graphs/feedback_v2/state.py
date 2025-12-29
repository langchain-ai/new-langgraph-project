from typing import TypedDict, List, Dict, Annotated, Any
from .schemas import AgentOutput

def merge_outputs(existing: List[AgentOutput], new: List[AgentOutput]) -> List[AgentOutput]:
    """Reducer to append new agent outputs to the state."""
    if not isinstance(new, list):
        # Handle single item being returned
        return existing + [new]
    return existing + new

class FeedbackState(TypedDict):
    """Global state for the feedback graph."""
    
    # Static inputs (read-only)
    code: str
    exercise_description: str
    
    # Mutable state
    results: Annotated[List[AgentOutput], merge_outputs]
    retry_counts: Dict[str, int]  # Track retries per agent
    aggregated_feedback: Dict[str, Any] # Final result
