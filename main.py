import os
import yaml
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import agents and state
from src.core.shared_state import SharedState
from src.agents.orchestrator import Orchestrator
from src.agents.static_analyzer import StaticAnalyzer
from src.agents.compiler_runner import CompilerRunner
from src.agents.unit_tester import UnitTester
from src.agents.rubric_scorer import RubricScorer

def main():
    """
    Main function to run the full grading pipeline.
    """
    print("Starting MagGradeAI grading pipeline...")

    # --- 1. Initialize State ---
    # Define paths for the submission and rubric
    submission_path = "./sample_submission"
    rubric_path = "./rubrics/example_assignment.yml"

    # Load the rubric file
    try:
        with open(rubric_path, 'r', encoding='utf-8') as f:
            rubric = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Rubric file not found at {rubric_path}")
        return
    except yaml.YAMLError as e:
        print(f"Error parsing YAML rubric: {e}")
        return

    # Create the initial shared state
    initial_state: SharedState = {
        "submission_path": submission_path,
        "rubric_path": rubric_path,
        "rubric": rubric,
        "findings": {},
        "grading_result": None,  # Initialize grading_result as None
    }

    # --- 2. Initialize Agents ---
    print("Initializing agents...")
    orchestrator = Orchestrator()
    static_analyzer = StaticAnalyzer()
    compiler_runner = CompilerRunner()
    unit_tester = UnitTester()
    rubric_scorer = RubricScorer()

    # --- 3. Run the Grading Pipeline ---
    # The sequence of agents is run manually here.
    # In a more advanced setup, this could be a dynamic graph determined by the orchestrator.
    print("Executing grading pipeline...")
    
    state = orchestrator.run(initial_state)
    state = static_analyzer.run(state)
    state = compiler_runner.run(state)
    state = unit_tester.run(state)
    final_state = rubric_scorer.run(state)

    # --- 4. Display Final Grade ---
    print("\n--- Grading Complete ---")
    if final_state.get("grading_result"):
        import json
        print(json.dumps(final_state["grading_result"], indent=2, ensure_ascii=False))
    else:
        print("No final grade was generated.")
    
    print("\nPipeline finished. Check your LangSmith project for traces.")

if __name__ == "__main__":
    # Ensure API keys are set
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("LANGCHAIN_API_KEY"):
        print("Error: Make sure OPENAI_API_KEY and LANGCHAIN_API_KEY are set in your .env file.")
    else:
        main()
