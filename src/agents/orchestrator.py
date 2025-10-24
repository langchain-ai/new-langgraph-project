
import os
import openai

from dotenv import load_dotenv
from langsmith import traceable

from src.core.shared_state import SharedState

load_dotenv()

class Orchestrator:
    """
    The Orchestrator agent reads the grading task and the rubric,
    and then decides which checks (other agents) need to be run.
    """

    def __init__(self):
        """Initializes the Orchestrator agent, setting up the OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        self.client = openai.OpenAI(api_key=api_key)

    @traceable
    def run(self, state: SharedState) -> SharedState:
        """
        The main entry point for the orchestrator.

        Args:
            state: The current shared state.

        Returns:
            The updated shared state.
        """
        print("Orchestrator: Reading task and rubric...")
        
        # Placeholder: Load the rubric YAML file based on the path in the state.
        # This would involve reading the file and parsing it.
        
        # Placeholder: Use the OpenAI client to interpret the rubric and decide the agent sequence.
        # For example:
        # response = self.client.chat.completions.create(
        #     model="gpt-4",
        #     messages=[
        #         {"role": "system", "content": "You are a helpful assistant that plans grading tasks."},
        #         {"role": "user", "content": f"Based on this rubric, what checks should I run?: {state.get('rubric')}"}
        #     ]
        # )
        
        print("Orchestrator: Decision made. Proceeding to the first check.")
        
        # The updated state would typically include the parsed rubric
        # and a plan or queue of agents to be executed.
        return state
