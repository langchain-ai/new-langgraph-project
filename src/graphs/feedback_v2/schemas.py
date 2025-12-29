from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class AgentInput(BaseModel):
    """Input payload for all micro-agents."""
    code: str
    exercise_description: str
    previous_feedback: List[str] = Field(default_factory=list, description="History of feedback from previous attempts in this session")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Any extra context")

class AgentOutput(BaseModel):
    """Standardized output from all micro-agents."""
    agent_name: str
    status: str = Field(..., description="'PASS', 'FAIL', or 'WARNING'")
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    comments: List[str] = Field(default_factory=list, description="List of specific feedback items")
    reasoning: str = Field("", description="Internal reasoning for the result")

class ValidationResult(BaseModel):
    """Output from a Validator node."""
    is_valid: bool
    retry_message: Optional[str] = None
    corrected_output: Optional[AgentOutput] = None
