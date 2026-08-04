"""
Integration tests for Whisper Modal server

These tests verify that the Whisper Modal server is properly deployed
and functioning correctly.

To run these tests:
    pytest tests/test_whisper_integration.py -v

Prerequisites:
    - WHISPER_API_URL environment variable set
    - Modal Whisper server deployed
    - Test audio file available
"""

import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

from src.whisper_client import WhisperClient, WhisperTranscriptionResult, transcribe

# Load environment
load_dotenv()


@pytest.fixture
def whisper_client():
    """Create a WhisperClient instance for testing."""
    return WhisperClient()


@pytest.fixture
def sample_audio():
    """Path to sample audio file for testing.

    Note: You'll need to provide an actual audio file for integration tests.
    For unit tests, we can mock the API responses.
    """
    # Check for sample audio in test fixtures
    test_audio = Path(__file__).parent / "fixtures" / "test_audio.mp3"

    if test_audio.exists():
        return str(test_audio)

    # Fallback to project root
    return "test_audio.mp3"


class TestWhisperClient:
    """Test WhisperClient functionality."""

    def test_client_initialization(self):
        """Test that client can be initialized."""
        client = WhisperClient()
        assert client is not None
        assert client.model_size == "base"

    def test_client_with_custom_model(self):
        """Test client initialization with custom model size."""
        client = WhisperClient(model_size="small")
        assert client.model_size == "small"

    def test_client_with_api_url(self):
        """Test client initialization with API URL."""
        api_url = "https://test.modal.run"
        client = WhisperClient(api_url=api_url)
        assert client.api_url == api_url

    def test_client_reads_env_var(self):
        """Test that client reads WHISPER_API_URL from environment."""
        if os.getenv("WHISPER_API_URL"):
            client = WhisperClient()
            assert client.api_url == os.getenv("WHISPER_API_URL")


class TestWhisperTranscriptionResult:
    """Test WhisperTranscriptionResult data class."""

    def test_successful_result(self):
        """Test successful transcription result."""
        data = {
            "text": "This is a test transcription",
            "language": "en",
            "segments": [
                {"text": "This is a test", "start": 0.0, "end": 1.5},
                {"text": "transcription", "start": 1.5, "end": 2.5},
            ],
            "model_size": "base",
        }

        result = WhisperTranscriptionResult(data)

        assert result.success is True
        assert result.text == "This is a test transcription"
        assert result.language == "en"
        assert len(result.segments) == 2
        assert result.model_size == "base"
        assert result.error is None

    def test_error_result(self):
        """Test error transcription result."""
        data = {
            "error": "Transcription failed",
            "text": "",
        }

        result = WhisperTranscriptionResult(data)

        assert result.success is False
        assert result.error == "Transcription failed"
        assert result.text == ""

    def test_result_string_representation(self):
        """Test string representation of result."""
        data = {"text": "Test", "language": "en"}
        result = WhisperTranscriptionResult(data)

        assert "Test" in str(result)
        assert "en" in str(result)


class TestWhisperIntegration:
    """Integration tests requiring actual Whisper API."""

    def test_health_check(self, whisper_client):
        """Test API health check endpoint."""
        if not os.getenv("WHISPER_API_URL"):
            pytest.skip("WHISPER_API_URL not set")

        is_healthy = whisper_client.health_check()
        assert is_healthy is True, "Whisper API should be healthy"

    def test_transcribe_missing_file(self, whisper_client):
        """Test transcription of non-existent file."""
        result = whisper_client.transcribe("nonexistent_file.mp3")

        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.skipif(
        not os.getenv("WHISPER_API_URL"),
        reason="WHISPER_API_URL not configured"
    )
    def test_transcribe_audio_file(self, whisper_client, sample_audio):
        """Test actual audio transcription."""
        if not Path(sample_audio).exists():
            pytest.skip(f"Sample audio file not found: {sample_audio}")

        result = whisper_client.transcribe(sample_audio)

        # Should successfully transcribe
        assert result.success is True, f"Transcription failed: {result.error}"
        assert len(result.text) > 0, "Transcription text should not be empty"
        assert result.language in ["en", "unknown"], "Should detect language"
        assert len(result.segments) > 0, "Should have segments"

    @pytest.mark.skipif(
        not os.getenv("WHISPER_API_URL"),
        reason="WHISPER_API_URL not configured"
    )
    def test_transcribe_with_language(self, whisper_client, sample_audio):
        """Test transcription with specified language."""
        if not Path(sample_audio).exists():
            pytest.skip(f"Sample audio file not found: {sample_audio}")

        result = whisper_client.transcribe(
            sample_audio,
            language="en"
        )

        assert result.success is True
        assert result.language == "en"

    @pytest.mark.skipif(
        not os.getenv("WHISPER_API_URL"),
        reason="WHISPER_API_URL not configured"
    )
    def test_transcribe_with_different_models(self, sample_audio):
        """Test transcription with different model sizes."""
        if not Path(sample_audio).exists():
            pytest.skip(f"Sample audio file not found: {sample_audio}")

        models = ["tiny", "base"]

        for model_size in models:
            client = WhisperClient(model_size=model_size)
            result = client.transcribe(sample_audio)

            assert result.success is True, f"Model {model_size} failed"
            assert result.model_size == model_size
            assert len(result.text) > 0

    @pytest.mark.skipif(
        not os.getenv("WHISPER_API_URL"),
        reason="WHISPER_API_URL not configured"
    )
    def test_convenience_function(self, sample_audio):
        """Test the convenience transcribe function."""
        if not Path(sample_audio).exists():
            pytest.skip(f"Sample audio file not found: {sample_audio}")

        result = transcribe(sample_audio, language="en")

        assert result.success is True
        assert len(result.text) > 0


class TestWhisperAsync:
    """Test async functionality."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv("WHISPER_API_URL"),
        reason="WHISPER_API_URL not configured"
    )
    async def test_async_transcription(self, sample_audio):
        """Test async transcription."""
        if not Path(sample_audio).exists():
            pytest.skip(f"Sample audio file not found: {sample_audio}")

        client = WhisperClient()
        result = await client.transcribe_async(sample_audio)

        assert result.success is True
        assert len(result.text) > 0


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_no_api_url_configured(self):
        """Test behavior when no API URL is configured."""
        # Temporarily clear environment variable
        original_url = os.environ.get("WHISPER_API_URL")
        if "WHISPER_API_URL" in os.environ:
            del os.environ["WHISPER_API_URL"]

        client = WhisperClient()
        result = client.transcribe("test.mp3")

        # Should return error about missing API URL
        assert result.success is False
        assert "API URL" in result.error or "not found" in result.error

        # Restore environment variable
        if original_url:
            os.environ["WHISPER_API_URL"] = original_url

    def test_invalid_model_size_handled(self, whisper_client, sample_audio):
        """Test that invalid model size is handled gracefully."""
        if not Path(sample_audio).exists():
            pytest.skip(f"Sample audio file not found: {sample_audio}")

        # This should be caught by the API validation
        result = whisper_client.transcribe(
            sample_audio,
            model_size="invalid_model"
        )

        # Should either fail or use default
        # Exact behavior depends on API implementation
        assert isinstance(result, WhisperTranscriptionResult)


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test requiring live API"
    )


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
