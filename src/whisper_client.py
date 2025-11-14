"""
Whisper Client for VoicedForm

This module provides a client interface to the Modal Whisper server for
transcribing audio in the VoicedForm application.

The client supports two modes:
1. Direct Modal function calls (when running in Modal environment)
2. HTTP API calls (when running locally or from other environments)
"""

import os
from pathlib import Path
from typing import Optional, Union, Literal
import warnings


class WhisperTranscriptionResult:
    """
    Represents the result of a Whisper transcription.

    Attributes:
        text: The full transcribed text
        language: Detected or specified language code
        segments: List of transcription segments with timing
        model_size: The Whisper model size used
        error: Error message if transcription failed
    """

    def __init__(self, data: dict):
        self.text = data.get("text", "")
        self.language = data.get("language", "unknown")
        self.segments = data.get("segments", [])
        self.model_size = data.get("model_size", "unknown")
        self.error = data.get("error")

    @property
    def success(self) -> bool:
        """Returns True if transcription was successful."""
        return bool(self.text and not self.error)

    def __str__(self) -> str:
        if self.error:
            return f"WhisperTranscriptionResult(error={self.error})"
        return f"WhisperTranscriptionResult(text='{self.text[:50]}...', language={self.language})"

    def __repr__(self) -> str:
        return self.__str__()


class WhisperClient:
    """
    Client for interacting with the Modal Whisper server.

    This client provides a high-level interface for transcribing audio files
    using the Modal-hosted Whisper service. It automatically handles both
    direct Modal function calls and HTTP API requests.

    Example:
        >>> client = WhisperClient(api_url="https://your-modal-app.modal.run")
        >>> result = client.transcribe("audio.mp3")
        >>> print(result.text)
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        model_size: Literal["tiny", "base", "small", "medium", "large"] = "base",
        use_direct_modal: bool = False,
    ):
        """
        Initialize the Whisper client.

        Args:
            api_url: URL of the Modal Whisper API (e.g., "https://your-app.modal.run")
                     Can also be set via WHISPER_API_URL environment variable
            model_size: Default Whisper model size to use
            use_direct_modal: If True, use direct Modal function calls instead of HTTP
        """
        self.api_url = api_url or os.getenv("WHISPER_API_URL")
        self.model_size = model_size
        self.use_direct_modal = use_direct_modal

        if not self.api_url and not use_direct_modal:
            warnings.warn(
                "No API URL provided and use_direct_modal=False. "
                "Set WHISPER_API_URL environment variable or pass api_url parameter.",
                UserWarning
            )

    def transcribe(
        self,
        audio: Union[str, Path, bytes],
        language: Optional[str] = None,
        task: Literal["transcribe", "translate"] = "transcribe",
        temperature: float = 0.0,
        initial_prompt: Optional[str] = None,
        model_size: Optional[str] = None,
    ) -> WhisperTranscriptionResult:
        """
        Transcribe audio to text using Whisper.

        Args:
            audio: Path to audio file or raw audio bytes
            language: ISO language code (e.g., 'en', 'es'). None for auto-detect.
            task: Either 'transcribe' or 'translate' (translate to English)
            temperature: Sampling temperature (0.0 = deterministic, more consistent)
            initial_prompt: Optional text to guide the transcription (e.g., proper nouns)
            model_size: Override default model size for this request

        Returns:
            WhisperTranscriptionResult with transcription text and metadata

        Example:
            >>> client = WhisperClient()
            >>> result = client.transcribe("audio.mp3", language="en")
            >>> if result.success:
            ...     print(f"Transcription: {result.text}")
        """
        # Read audio data
        if isinstance(audio, (str, Path)):
            audio_path = Path(audio)
            if not audio_path.exists():
                return WhisperTranscriptionResult({
                    "error": f"Audio file not found: {audio}",
                    "text": "",
                })
            audio_data = audio_path.read_bytes()
            filename = audio_path.name
        else:
            audio_data = audio
            filename = "audio.unknown"

        # Use specified model size or default
        model = model_size or self.model_size

        if self.use_direct_modal:
            return self._transcribe_direct(
                audio_data=audio_data,
                language=language,
                task=task,
                temperature=temperature,
                initial_prompt=initial_prompt,
                model_size=model,
            )
        else:
            return self._transcribe_http(
                audio_data=audio_data,
                filename=filename,
                language=language,
                task=task,
                temperature=temperature,
                initial_prompt=initial_prompt,
                model_size=model,
            )

    def _transcribe_direct(
        self,
        audio_data: bytes,
        language: Optional[str],
        task: str,
        temperature: float,
        initial_prompt: Optional[str],
        model_size: str,
    ) -> WhisperTranscriptionResult:
        """Use direct Modal function calls (requires modal package)."""
        try:
            from modal_whisper_server import WhisperModel

            model = WhisperModel(model_size=model_size)
            result = model.transcribe.remote(
                audio_data=audio_data,
                language=language,
                task=task,
                temperature=temperature,
                initial_prompt=initial_prompt,
            )
            return WhisperTranscriptionResult(result)

        except ImportError:
            return WhisperTranscriptionResult({
                "error": "Modal package not installed. Install with: pip install modal",
                "text": "",
            })
        except Exception as e:
            return WhisperTranscriptionResult({
                "error": f"Direct Modal transcription failed: {str(e)}",
                "text": "",
            })

    def _transcribe_http(
        self,
        audio_data: bytes,
        filename: str,
        language: Optional[str],
        task: str,
        temperature: float,
        initial_prompt: Optional[str],
        model_size: str,
    ) -> WhisperTranscriptionResult:
        """Use HTTP API calls to Modal Whisper server."""
        if not self.api_url:
            return WhisperTranscriptionResult({
                "error": "No API URL configured. Set WHISPER_API_URL or pass api_url to constructor.",
                "text": "",
            })

        try:
            import httpx

            url = f"{self.api_url.rstrip('/')}/transcribe"

            # Prepare form data
            files = {"audio": (filename, audio_data)}
            data = {
                "model_size": model_size,
                "task": task,
                "temperature": str(temperature),
            }

            if language:
                data["language"] = language

            if initial_prompt:
                data["initial_prompt"] = initial_prompt

            # Make request with timeout
            with httpx.Client(timeout=300.0) as client:  # 5 minute timeout
                response = client.post(url, files=files, data=data)
                response.raise_for_status()
                result = response.json()

            return WhisperTranscriptionResult(result)

        except ImportError:
            return WhisperTranscriptionResult({
                "error": "httpx package not installed. Install with: pip install httpx",
                "text": "",
            })
        except Exception as e:
            return WhisperTranscriptionResult({
                "error": f"HTTP transcription failed: {str(e)}",
                "text": "",
            })

    async def transcribe_async(
        self,
        audio: Union[str, Path, bytes],
        language: Optional[str] = None,
        task: Literal["transcribe", "translate"] = "transcribe",
        temperature: float = 0.0,
        initial_prompt: Optional[str] = None,
        model_size: Optional[str] = None,
    ) -> WhisperTranscriptionResult:
        """
        Async version of transcribe() for use in async contexts.

        Args: Same as transcribe()

        Returns:
            WhisperTranscriptionResult with transcription text and metadata
        """
        # Read audio data
        if isinstance(audio, (str, Path)):
            audio_path = Path(audio)
            if not audio_path.exists():
                return WhisperTranscriptionResult({
                    "error": f"Audio file not found: {audio}",
                    "text": "",
                })
            audio_data = audio_path.read_bytes()
            filename = audio_path.name
        else:
            audio_data = audio
            filename = "audio.unknown"

        model = model_size or self.model_size

        if not self.api_url:
            return WhisperTranscriptionResult({
                "error": "No API URL configured. Set WHISPER_API_URL or pass api_url to constructor.",
                "text": "",
            })

        try:
            import httpx

            url = f"{self.api_url.rstrip('/')}/transcribe"

            files = {"audio": (filename, audio_data)}
            data = {
                "model_size": model,
                "task": task,
                "temperature": str(temperature),
            }

            if language:
                data["language"] = language

            if initial_prompt:
                data["initial_prompt"] = initial_prompt

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(url, files=files, data=data)
                response.raise_for_status()
                result = response.json()

            return WhisperTranscriptionResult(result)

        except ImportError:
            return WhisperTranscriptionResult({
                "error": "httpx package not installed. Install with: pip install httpx",
                "text": "",
            })
        except Exception as e:
            return WhisperTranscriptionResult({
                "error": f"Async HTTP transcription failed: {str(e)}",
                "text": "",
            })

    def health_check(self) -> bool:
        """
        Check if the Whisper API is healthy and accessible.

        Returns:
            True if API is healthy, False otherwise
        """
        if not self.api_url:
            return False

        try:
            import httpx

            url = f"{self.api_url.rstrip('/')}/health"
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                return response.status_code == 200

        except Exception:
            return False


# Convenience function for quick transcription
def transcribe(
    audio: Union[str, Path, bytes],
    api_url: Optional[str] = None,
    model_size: str = "base",
    language: Optional[str] = None,
) -> WhisperTranscriptionResult:
    """
    Quick transcription function for simple use cases.

    Args:
        audio: Path to audio file or raw audio bytes
        api_url: URL of Modal Whisper API (or set WHISPER_API_URL env var)
        model_size: Whisper model size to use
        language: Optional language code for transcription

    Returns:
        WhisperTranscriptionResult with transcription

    Example:
        >>> from src.whisper_client import transcribe
        >>> result = transcribe("audio.mp3", language="en")
        >>> print(result.text)
    """
    client = WhisperClient(api_url=api_url, model_size=model_size)
    return client.transcribe(audio, language=language)
