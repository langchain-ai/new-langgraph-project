"""
Modal Whisper Server for VoicedForm

This module provides a serverless Whisper speech-to-text service using Modal.
It supports multiple Whisper model sizes and provides a REST API for transcription.

Key Features:
- Serverless deployment on Modal infrastructure
- Multiple Whisper model sizes (tiny, base, small, medium, large)
- Automatic model caching for fast cold starts
- RESTful API with FastAPI
- Support for various audio formats
- Language detection and multilingual support
"""

import io
import os
from pathlib import Path
from typing import Optional

import modal

# Modal configuration
APP_NAME = "voicedform-whisper"
GPU_CONFIG = modal.gpu.A10G()  # Good balance of cost and performance for Whisper

# Create Modal app
app = modal.App(APP_NAME)

# Define the Modal image with all required dependencies
whisper_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")  # Required for audio processing
    .pip_install(
        "openai-whisper==20231117",
        "torch==2.1.2",
        "torchaudio==2.1.2",
        "fastapi[standard]==0.115.4",
        "python-multipart==0.0.12",
    )
)

# Volume for model caching
model_cache = modal.Volume.from_name("whisper-model-cache", create_if_missing=True)
MODEL_CACHE_DIR = "/cache/whisper"


@app.cls(
    image=whisper_image,
    gpu=GPU_CONFIG,
    volumes={MODEL_CACHE_DIR: model_cache},
    container_idle_timeout=300,  # Keep warm for 5 minutes
    timeout=600,  # 10 minute max execution time
)
class WhisperModel:
    """
    Modal class for running Whisper speech-to-text inference.

    The model is loaded on container start and cached to the volume for fast
    subsequent cold starts.
    """

    model_size: str = "base"  # Default model size

    @modal.build()
    def download_model(self):
        """Download and cache the Whisper model during image build."""
        import whisper

        # Download model to cache directory
        whisper.load_model(
            self.model_size,
            download_root=MODEL_CACHE_DIR
        )
        print(f"✓ Downloaded Whisper {self.model_size} model to cache")

    @modal.enter()
    def load_model(self):
        """Load the Whisper model when container starts."""
        import whisper
        import torch

        print(f"Loading Whisper {self.model_size} model...")

        # Set cache directory
        os.environ["WHISPER_CACHE_DIR"] = MODEL_CACHE_DIR

        # Load model from cache
        self.model = whisper.load_model(
            self.model_size,
            download_root=MODEL_CACHE_DIR
        )

        # Check if GPU is available
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"✓ Loaded Whisper {self.model_size} model on {self.device}")

    @modal.method()
    def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        task: str = "transcribe",
        temperature: float = 0.0,
        initial_prompt: Optional[str] = None,
    ) -> dict:
        """
        Transcribe audio data to text using Whisper.

        Args:
            audio_data: Raw audio file bytes (any format supported by ffmpeg)
            language: ISO language code (e.g., 'en', 'es'). None for auto-detect.
            task: Either 'transcribe' or 'translate' (to English)
            temperature: Sampling temperature (0.0 = deterministic)
            initial_prompt: Optional text to guide the model

        Returns:
            dict: Transcription result with text, segments, and metadata
        """
        import tempfile
        import whisper

        try:
            # Write audio bytes to temporary file
            with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp_file:
                tmp_file.write(audio_data)
                tmp_path = tmp_file.name

            # Prepare transcription options
            options = {
                "task": task,
                "temperature": temperature,
            }

            if language:
                options["language"] = language

            if initial_prompt:
                options["initial_prompt"] = initial_prompt

            # Transcribe
            result = self.model.transcribe(tmp_path, **options)

            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

            # Return formatted result
            return {
                "text": result["text"].strip(),
                "language": result.get("language", "unknown"),
                "segments": [
                    {
                        "text": seg["text"].strip(),
                        "start": seg["start"],
                        "end": seg["end"],
                    }
                    for seg in result.get("segments", [])
                ],
                "model_size": self.model_size,
            }

        except Exception as e:
            return {
                "error": str(e),
                "text": "",
                "language": "unknown",
                "segments": [],
            }


# FastAPI web endpoint
@app.function(
    image=whisper_image,
)
@modal.asgi_app()
def fastapi_app():
    """
    FastAPI application for REST API access to Whisper transcription.

    Endpoints:
        POST /transcribe - Transcribe audio file
        GET /health - Health check
        GET / - API documentation
    """
    from fastapi import FastAPI, File, UploadFile, Form, HTTPException
    from fastapi.responses import JSONResponse

    web_app = FastAPI(
        title="VoicedForm Whisper API",
        description="Speech-to-text transcription service using OpenAI Whisper",
        version="1.0.0",
    )

    @web_app.get("/")
    async def root():
        """API documentation and information."""
        return {
            "service": "VoicedForm Whisper API",
            "version": "1.0.0",
            "endpoints": {
                "POST /transcribe": "Transcribe audio file to text",
                "GET /health": "Health check endpoint",
            },
            "supported_formats": [
                "mp3", "wav", "m4a", "ogg", "flac", "webm", "mp4"
            ],
            "models": ["tiny", "base", "small", "medium", "large"],
        }

    @web_app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy", "service": "whisper-api"}

    @web_app.post("/transcribe")
    async def transcribe_audio(
        audio: UploadFile = File(..., description="Audio file to transcribe"),
        model_size: str = Form("base", description="Whisper model size"),
        language: Optional[str] = Form(None, description="ISO language code (e.g., 'en')"),
        task: str = Form("transcribe", description="'transcribe' or 'translate'"),
        temperature: float = Form(0.0, description="Sampling temperature"),
        initial_prompt: Optional[str] = Form(None, description="Optional text to guide transcription"),
    ):
        """
        Transcribe an audio file to text.

        Upload an audio file and receive the transcribed text along with
        timing information for each segment.
        """
        # Validate model size
        valid_models = ["tiny", "base", "small", "medium", "large"]
        if model_size not in valid_models:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model_size. Must be one of: {valid_models}"
            )

        # Validate task
        if task not in ["transcribe", "translate"]:
            raise HTTPException(
                status_code=400,
                detail="Task must be either 'transcribe' or 'translate'"
            )

        try:
            # Read audio file
            audio_data = await audio.read()

            if len(audio_data) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Empty audio file"
                )

            # Create model instance with specified size
            model = WhisperModel(model_size=model_size)

            # Transcribe
            result = model.transcribe.remote(
                audio_data=audio_data,
                language=language,
                task=task,
                temperature=temperature,
                initial_prompt=initial_prompt,
            )

            # Check for errors
            if "error" in result and result["error"]:
                raise HTTPException(
                    status_code=500,
                    detail=f"Transcription error: {result['error']}"
                )

            return JSONResponse(content=result)

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )


# CLI for local testing and deployment
@app.local_entrypoint()
def main(
    audio_file: str = "test.mp3",
    model_size: str = "base",
    language: Optional[str] = None,
):
    """
    Local CLI for testing Whisper transcription.

    Usage:
        modal run modal_whisper_server.py --audio-file path/to/audio.mp3
    """
    from pathlib import Path

    audio_path = Path(audio_file)

    if not audio_path.exists():
        print(f"Error: Audio file not found: {audio_file}")
        return

    print(f"Transcribing {audio_file} with {model_size} model...")

    # Read audio file
    audio_data = audio_path.read_bytes()

    # Create model and transcribe
    model = WhisperModel(model_size=model_size)
    result = model.transcribe.remote(
        audio_data=audio_data,
        language=language,
    )

    # Print results
    print("\n" + "=" * 80)
    print("TRANSCRIPTION RESULT")
    print("=" * 80)
    print(f"\nText: {result['text']}")
    print(f"Language: {result['language']}")
    print(f"Model: {result['model_size']}")
    print(f"\nSegments ({len(result['segments'])}):")
    for i, seg in enumerate(result['segments'], 1):
        print(f"  [{seg['start']:.2f}s - {seg['end']:.2f}s] {seg['text']}")
    print("=" * 80)
