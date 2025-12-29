import sys
import os
from unittest.mock import MagicMock

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import graphs.feedback_v2.agents.base 
# Patch the class in the module where it is used
graphs.feedback_v2.agents.base.ChatOpenAI = MagicMock()

from graphs.feedback_v2.orchestrator import feedback_graph_v2
from graphs.feedback_v2.agents.base import BaseAgent

# Now we can safely invoke the graph which uses BaseAgent subclasses
# Mock the invoke method to avoid real LLM calls entirely just in case
def mock_invoke(self, inputs):
    from graphs.feedback_v2.schemas import AgentOutput
    return AgentOutput(
        agent_name=self.name,
        status="PASS",
        confidence_score=0.9,
        comments=[f"Mock feedback from {self.name}"],
        reasoning="Mock reasoning"
    )

# Patch BaseAgent.invoke
BaseAgent.original_invoke = BaseAgent.invoke
BaseAgent.invoke = mock_invoke

def run_verification():
    print("Starting verification of Feedback Graph V2...")
    
    mock_input = {
        "code": "def hello(): print('world')",
        "exercise_description": "Write a function that prints 'world'",
        "results": [],
        "retry_counts": {}, 
        "aggregated_feedback": {}
    }
    
    try:
        result = feedback_graph_v2.invoke(mock_input)
        print("\nGraph execution completed successfully!")
        
        aggregated = result.get("aggregated_feedback", {})
        print(f"\nFinal Status: {aggregated.get('status')}")
        print("Details:")
        for detail in aggregated.get("details", []):
            print(f"- {detail['agent_name']}: {detail['status']}")
            
        print("\nVERIFICATION PASSED")
        
    except Exception as e:
        print(f"\nVERIFICATION FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_verification()
