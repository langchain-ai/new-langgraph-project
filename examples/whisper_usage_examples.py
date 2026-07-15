"""
Whisper Usage Examples for VoicedForm

This file demonstrates various ways to use the Whisper integration
in VoicedForm for speech-to-text transcription.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import WhisperClient
from src.whisper_client import WhisperClient, transcribe


def example_1_basic_transcription():
    """
    Example 1: Basic transcription with default settings

    This is the simplest way to transcribe an audio file.
    """
    print("\n" + "=" * 80)
    print("Example 1: Basic Transcription")
    print("=" * 80)

    # Initialize client
    client = WhisperClient()

    # Transcribe audio file (replace with your actual file)
    audio_file = "sample_audio.mp3"

    if not Path(audio_file).exists():
        print(f"⚠️  Audio file not found: {audio_file}")
        print("   Please provide a real audio file to test.")
        return

    result = client.transcribe(audio_file)

    if result.success:
        print(f"✓ Success!")
        print(f"  Text: {result.text}")
        print(f"  Language: {result.language}")
        print(f"  Model: {result.model_size}")
    else:
        print(f"✗ Error: {result.error}")


def example_2_specify_language():
    """
    Example 2: Specify language for faster transcription

    If you know the language, specifying it speeds up transcription
    and improves accuracy.
    """
    print("\n" + "=" * 80)
    print("Example 2: Transcription with Language Specified")
    print("=" * 80)

    client = WhisperClient()

    # Transcribe with language specified (faster than auto-detect)
    result = client.transcribe(
        "sample_audio.mp3",
        language="en",  # English
    )

    if result.success:
        print(f"✓ Transcribed as English:")
        print(f"  {result.text}")


def example_3_different_model_sizes():
    """
    Example 3: Using different model sizes

    Demonstrates how to use different Whisper models based on your
    accuracy vs. speed requirements.
    """
    print("\n" + "=" * 80)
    print("Example 3: Different Model Sizes")
    print("=" * 80)

    audio_file = "sample_audio.mp3"

    if not Path(audio_file).exists():
        print(f"⚠️  Audio file not found, using placeholder")
        return

    models = ["tiny", "base", "small"]

    for model_size in models:
        print(f"\nTesting with {model_size} model...")
        client = WhisperClient(model_size=model_size)
        result = client.transcribe(audio_file)

        if result.success:
            print(f"  ✓ {model_size}: {result.text[:50]}...")


def example_4_translation():
    """
    Example 4: Translate to English

    Whisper can automatically translate non-English audio to English.
    """
    print("\n" + "=" * 80)
    print("Example 4: Translation to English")
    print("=" * 80)

    client = WhisperClient()

    # Translate Spanish audio to English
    result = client.transcribe(
        "spanish_audio.mp3",
        task="translate",  # Translate to English
    )

    if result.success:
        print(f"✓ Translated to English:")
        print(f"  {result.text}")
    else:
        print(f"ℹ️  Skipping - no Spanish audio file available")


def example_5_with_context():
    """
    Example 5: Providing context for better accuracy

    The initial_prompt helps guide Whisper to understand context,
    proper nouns, and domain-specific terminology.
    """
    print("\n" + "=" * 80)
    print("Example 5: Transcription with Context")
    print("=" * 80)

    client = WhisperClient()

    # Provide context about what the audio is about
    result = client.transcribe(
        "sample_audio.mp3",
        initial_prompt="This is an accident report form. "
                      "The speaker is describing a car accident on Main Street.",
        temperature=0.0,  # Deterministic output
    )

    if result.success:
        print(f"✓ Transcription with context:")
        print(f"  {result.text}")


def example_6_with_segments():
    """
    Example 6: Working with transcription segments

    Access individual segments with timing information for
    more detailed analysis.
    """
    print("\n" + "=" * 80)
    print("Example 6: Transcription Segments with Timing")
    print("=" * 80)

    client = WhisperClient()
    result = client.transcribe("sample_audio.mp3")

    if result.success:
        print(f"✓ Full text: {result.text}\n")
        print(f"  Segments ({len(result.segments)}):")

        for i, segment in enumerate(result.segments[:5], 1):  # Show first 5
            start = segment['start']
            end = segment['end']
            text = segment['text']
            print(f"  [{start:.1f}s - {end:.1f}s] {text}")


def example_7_convenience_function():
    """
    Example 7: Using the convenience function

    For quick, simple transcriptions without needing to create a client.
    """
    print("\n" + "=" * 80)
    print("Example 7: Convenience Function")
    print("=" * 80)

    # Quick one-line transcription
    result = transcribe(
        "sample_audio.mp3",
        model_size="base",
        language="en",
    )

    if result.success:
        print(f"✓ Quick transcription: {result.text}")


def example_8_async_transcription():
    """
    Example 8: Async transcription for concurrent operations

    Use async/await for transcribing multiple files concurrently.
    """
    print("\n" + "=" * 80)
    print("Example 8: Async Transcription")
    print("=" * 80)

    import asyncio

    async def transcribe_multiple_files():
        client = WhisperClient()

        audio_files = ["file1.mp3", "file2.mp3", "file3.mp3"]

        # Create tasks for concurrent transcription
        tasks = [
            client.transcribe_async(audio_file)
            for audio_file in audio_files
            if Path(audio_file).exists()
        ]

        # Wait for all transcriptions to complete
        results = await asyncio.gather(*tasks)

        for i, result in enumerate(results, 1):
            if result.success:
                print(f"  ✓ File {i}: {result.text[:50]}...")

    # Run async function
    if any(Path(f).exists() for f in ["file1.mp3", "file2.mp3", "file3.mp3"]):
        asyncio.run(transcribe_multiple_files())
    else:
        print("  ℹ️  No audio files found for async example")


def example_9_error_handling():
    """
    Example 9: Proper error handling

    Always check for errors and handle them appropriately.
    """
    print("\n" + "=" * 80)
    print("Example 9: Error Handling")
    print("=" * 80)

    client = WhisperClient()

    # Try to transcribe non-existent file
    result = client.transcribe("nonexistent.mp3")

    if result.success:
        print(f"✓ Text: {result.text}")
    else:
        print(f"✗ Expected error occurred: {result.error}")

    # Check API health before transcribing
    if client.health_check():
        print("✓ API is healthy, proceeding with transcription...")
    else:
        print("✗ API is not accessible. Please check WHISPER_API_URL.")


def example_10_integration_with_voicedform():
    """
    Example 10: Integration with VoicedForm workflow

    Show how to use Whisper transcription in the full VoicedForm graph.
    """
    print("\n" + "=" * 80)
    print("Example 10: VoicedForm Integration")
    print("=" * 80)

    try:
        from voicedform_graph_with_audio import process_voice_input, process_text_input

        # Process voice input through full workflow
        audio_file = "accident_report.mp3"

        if Path(audio_file).exists():
            print(f"Processing voice input: {audio_file}")
            result = process_voice_input(audio_file)

            print(f"\n✓ Workflow complete!")
            print(f"  Transcribed: {result.get('transcribed_text', 'N/A')[:50]}...")
            print(f"  Form Type: {result.get('form_type')}")
            print(f"  Valid: {result.get('valid')}")
        else:
            # Fallback to text input
            print("No audio file, using text input instead")
            result = process_text_input(
                "I need to report an accident that happened on Main Street today"
            )
            print(f"\n✓ Text workflow complete!")
            print(f"  Form Type: {result.get('form_type')}")
            print(f"  Valid: {result.get('valid')}")

    except ImportError:
        print("  ℹ️  VoicedForm graph module not available")


def main():
    """Run all examples"""

    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "WHISPER USAGE EXAMPLES" + " " * 35 + "║")
    print("╚" + "=" * 78 + "╝")

    # Check environment
    api_url = os.getenv("WHISPER_API_URL")
    if not api_url:
        print("\n⚠️  WARNING: WHISPER_API_URL not set!")
        print("   Set it in .env or export WHISPER_API_URL=your_modal_url")
        print("   Some examples will fail without it.\n")

    # Run examples
    examples = [
        example_1_basic_transcription,
        example_2_specify_language,
        example_3_different_model_sizes,
        example_4_translation,
        example_5_with_context,
        example_6_with_segments,
        example_7_convenience_function,
        example_8_async_transcription,
        example_9_error_handling,
        example_10_integration_with_voicedform,
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n✗ Example failed: {e}")

    print("\n" + "=" * 80)
    print("Examples complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
