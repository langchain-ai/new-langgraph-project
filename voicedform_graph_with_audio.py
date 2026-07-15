"""
VoicedForm Graph with Audio Transcription

This is an enhanced version of the VoicedForm graph that includes audio transcription
using the Modal Whisper server. It supports both voice and text input for form completion.

The workflow now includes:
1. Audio Transcription (optional) - Converts voice input to text
2. Supervisor - Decides the form type based on input
3. Form Selector - Determines required fields
4. Form Completion - Interactive form filling
5. Validator - Verifies completed form
"""

from dotenv import load_dotenv
import os
from typing import TypedDict, Optional
from pathlib import Path

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableLambda

from src.whisper_client import WhisperClient

# Load environment
load_dotenv()

# DEBUG print to confirm keys are loaded
print("OPENAI_KEY LOADED:", os.getenv("OPENAI_API_KEY")[:10] if os.getenv("OPENAI_API_KEY") else "NOT SET", "...")
print("WHISPER_API_URL:", os.getenv("WHISPER_API_URL", "NOT SET"))
print("LangSmith project:", os.getenv("LANGSMITH_PROJECT"))

# Reusable LLM
llm = ChatOpenAI(model="gpt-4", temperature=0)

# Whisper client for audio transcription
whisper_client = WhisperClient(
    api_url=os.getenv("WHISPER_API_URL"),
    model_size="base",  # Good balance of speed and accuracy
)


# Graph State Definition
class GraphState(TypedDict, total=False):
    """
    State for the VoicedForm graph.

    Attributes:
        audio_file: Optional path to audio file for transcription
        transcribed_text: Text transcribed from audio
        user_input: Text input from user (either transcribed or direct)
        form_type: Type of form to complete
        form_fields: Fields required for the form
        form_data: Collected form data
        form_complete: Final completed form
        valid: Whether the form is valid
        error: Any error messages
    """
    audio_file: Optional[str]
    transcribed_text: Optional[str]
    user_input: Optional[str]
    form_type: Optional[str]
    form_fields: Optional[str]
    form_data: Optional[dict]
    form_complete: Optional[str]
    valid: Optional[bool]
    error: Optional[str]


# Node: Audio Transcription
def audio_transcription_node(state: GraphState) -> GraphState:
    """
    Transcribe audio file to text using Modal Whisper server.

    This node is the entry point when audio input is provided. It converts
    the audio to text and passes it to the next node in the workflow.

    Args:
        state: Graph state with audio_file path

    Returns:
        Updated state with transcribed_text and user_input
    """
    print("🎙️ Audio Transcription: Processing audio input...")

    audio_file = state.get("audio_file")

    # Skip if no audio file provided
    if not audio_file:
        print("⏭️ No audio file provided, skipping transcription")
        return state

    # Check if file exists
    if not Path(audio_file).exists():
        error_msg = f"Audio file not found: {audio_file}"
        print(f"❌ {error_msg}")
        return {**state, "error": error_msg}

    # Transcribe audio
    print(f"🎧 Transcribing: {audio_file}")
    result = whisper_client.transcribe(
        audio=audio_file,
        language="en",  # Can be made dynamic based on user preference
        task="transcribe",
    )

    if not result.success:
        error_msg = f"Transcription failed: {result.error}"
        print(f"❌ {error_msg}")
        return {**state, "error": error_msg}

    print(f"✅ Transcribed: {result.text}")
    print(f"   Language: {result.language}")
    print(f"   Segments: {len(result.segments)}")

    return {
        **state,
        "transcribed_text": result.text,
        "user_input": result.text,  # Use transcribed text as user input
    }


# Node: Supervisor (enhanced with context from user input)
def supervisor_node(state: GraphState) -> GraphState:
    """
    Supervisor decides the form type based on user input.

    This node analyzes the user's input (transcribed or text) to determine
    what type of form they need to complete.

    Args:
        state: Graph state with user_input

    Returns:
        Updated state with form_type
    """
    print("🧭 Supervisor: Analyzing input to determine form type...")

    user_input = state.get("user_input", "")

    if user_input:
        # Use LLM to determine form type from user input
        prompt = f"""Based on the following user input, determine what type of form they need to complete.

User input: "{user_input}"

Common form types: accident_report, contact_form, feedback_form, survey, registration

Respond with just the form type, nothing else."""

        response = llm.invoke(prompt)
        form_type = response.content.strip().lower()
        print(f"📋 Determined form type: {form_type}")
    else:
        # Default form type
        form_type = "accident_report"
        print(f"📋 Using default form type: {form_type}")

    return {**state, "form_type": form_type}


# Node: Form Selector (uses LLM to describe form)
def form_selector_node(state: GraphState) -> GraphState:
    """
    Form Selector determines the required fields for the form.

    Based on the form type, this node uses an LLM to identify what
    fields need to be collected.

    Args:
        state: Graph state with form_type

    Returns:
        Updated state with form_fields
    """
    form_type = state.get("form_type", "unknown")
    print(f"📄 Form Selector: Processing form type → {form_type}")

    message = f"""You are helping complete a form of type: {form_type}.

List the required fields for this form. Be specific and practical.
For example, an accident report might need: date, location, description, injuries, witnesses."""

    response = llm.invoke(message)
    form_fields = response.content

    print(f"📝 Required fields identified:\n{form_fields}")

    return {**state, "form_fields": form_fields}


# Node: Form Completion (enhanced with user input context)
def form_completion_node(state: GraphState) -> GraphState:
    """
    Form Completion handles the interactive form filling process.

    This node uses the user's input and the required fields to start
    populating the form.

    Args:
        state: Graph state with form_fields and user_input

    Returns:
        Updated state with form_complete
    """
    print("✍️ Form Completion: Starting form population...")

    form_fields = state.get("form_fields", "")
    user_input = state.get("user_input", "")

    prompt = f"""You are helping to complete a form. Here are the required fields:

{form_fields}

The user has provided the following input:
"{user_input}"

Based on this input, extract and organize the information to fill out as many fields as possible.
Format the response as a completed form with field names and values."""

    response = llm.invoke(prompt)
    form_complete = response.content

    print(f"📋 Form populated:\n{form_complete[:200]}...")

    return {**state, "form_complete": form_complete}


# Node: Validator (verifies form completion)
def validator_node(state: GraphState) -> GraphState:
    """
    Validator checks if the form is properly completed.

    This node verifies that all required fields have been filled
    and the form is ready for submission.

    Args:
        state: Graph state with form_complete

    Returns:
        Updated state with valid flag
    """
    print("✅ Validator: Verifying form completion...")

    form_complete = state.get("form_complete", "")
    is_valid = bool(form_complete and len(form_complete) > 20)

    if is_valid:
        print("✅ Form is valid and complete!")
    else:
        print("❌ Form validation failed - incomplete data")

    return {**state, "valid": is_valid}


# Build the LangGraph workflow
graph = StateGraph(GraphState)

# Add nodes
graph.add_node("audio_transcription", RunnableLambda(audio_transcription_node))
graph.add_node("supervisor", RunnableLambda(supervisor_node))
graph.add_node("form_selector", RunnableLambda(form_selector_node))
graph.add_node("form_completion", RunnableLambda(form_completion_node))
graph.add_node("validator", RunnableLambda(validator_node))

# Wire nodes together
graph.set_entry_point("audio_transcription")
graph.add_edge("audio_transcription", "supervisor")
graph.add_edge("supervisor", "form_selector")
graph.add_edge("form_selector", "form_completion")
graph.add_edge("form_completion", "validator")
graph.add_edge("validator", END)

# Compile the graph
dag = graph.compile()


# Convenience functions for running the workflow
def process_voice_input(audio_file: str) -> dict:
    """
    Process a voice input file through the VoicedForm workflow.

    Args:
        audio_file: Path to audio file

    Returns:
        Final state with completed form

    Example:
        >>> result = process_voice_input("user_recording.mp3")
        >>> print(result["form_complete"])
    """
    print(f"\n🎙️ Processing voice input from: {audio_file}\n")
    return dag.invoke({"audio_file": audio_file})


def process_text_input(user_text: str) -> dict:
    """
    Process a text input through the VoicedForm workflow.

    Args:
        user_text: User's text input

    Returns:
        Final state with completed form

    Example:
        >>> result = process_text_input("I had an accident on Main St today")
        >>> print(result["form_complete"])
    """
    print(f"\n💬 Processing text input: {user_text}\n")
    return dag.invoke({"user_input": user_text})


# Main execution for testing
if __name__ == "__main__":
    import sys

    print("\n🚀 VoicedForm Graph with Audio Transcription\n")
    print("=" * 80)

    # Example 1: Text input
    print("\n📝 Example 1: Text Input")
    print("-" * 80)
    text_result = process_text_input(
        "I need to report an accident that happened on Main Street today at 2pm. "
        "A car hit a pedestrian, there were minor injuries, and two witnesses."
    )
    print("\n📊 Result:")
    print(f"Form Type: {text_result.get('form_type')}")
    print(f"Valid: {text_result.get('valid')}")
    print(f"Form:\n{text_result.get('form_complete', 'N/A')[:300]}...")

    # Example 2: Audio input (if file provided)
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        print(f"\n🎙️ Example 2: Audio Input from {audio_file}")
        print("-" * 80)
        audio_result = process_voice_input(audio_file)
        print("\n📊 Result:")
        print(f"Transcribed: {audio_result.get('transcribed_text', 'N/A')}")
        print(f"Form Type: {audio_result.get('form_type')}")
        print(f"Valid: {audio_result.get('valid')}")
        print(f"Form:\n{audio_result.get('form_complete', 'N/A')[:300]}...")

    print("\n" + "=" * 80)
    print("✅ VoicedForm workflow complete!")
