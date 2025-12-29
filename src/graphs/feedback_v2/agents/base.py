from abc import ABC, abstractmethod
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from ..schemas import AgentInput, AgentOutput

class BaseAgent(ABC):
    """Abstract base class for all feedback micro-agents."""
    
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0):
        self.model = ChatOpenAI(model=model_name, temperature=temperature)
        self.parser = PydanticOutputParser(pydantic_object=AgentOutput)

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of this agent."""
        pass

    @property
    @abstractmethod
    def role_description(self) -> str:
        """Description of the agent's specific role/focus."""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the specific system prompt for this agent."""
        pass

    def invoke(self, inputs: AgentInput) -> AgentOutput:
        """Run the agent against the provided input."""
        
        system_prompt = f"""You are the {self.name}.
Role: {self.role_description}

You must analyze the student's code and provide feedback in JSON format.
{self.parser.get_format_instructions()}

IMPORTANT:
- Be strict but constructive.
- Focus ONLY on your specific role. Do not comment on things outside your scope.
- Return valid JSON matching the schema.
"""
        user_prompt = f"""
Exercise Description:
{inputs.exercise_description}

Student Code:
{inputs.code}

Previous Feedback (if any):
{inputs.previous_feedback}
"""
        messages = [
            SystemMessage(content=system_prompt),
            SystemMessage(content=self.get_system_prompt()), # Specific instructions
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = self.model.invoke(messages)
            parsed_output = self.parser.parse(response.content)
            # Enforce name consistency
            parsed_output.agent_name = self.name 
            return parsed_output
        except Exception as e:
            # Fallback for parsing errors
            return AgentOutput(
                agent_name=self.name,
                status="FAIL",
                confidence_score=0.0,
                comments=[f"Internal Error: Failed to generate valid feedback. Error: {str(e)}"],
                reasoning="Agent failed to produce parseable JSON."
            )
