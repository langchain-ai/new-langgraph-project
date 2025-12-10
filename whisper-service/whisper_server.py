"""
Whisper WebSocket Server for VoicedForm
Deployed on Modal.com for serverless GPU-accelerated transcription

To deploy:
1. Install Modal: pip install modal
2. Set up Modal token: modal token new
3. Deploy: modal deploy whisper_server.py
4. Get endpoint URL from Modal dashboard
5. Add WHISPER_WS_URL to your .env.local

Environment variables needed:
- WHISPER_MODEL (optional, default: base.en)
"""

import asyncio
import json
import logging
from typing import Set

import modal
import numpy as np

# Create Modal app
app = modal.App("voicedform-whisper")

# Define container image with Whisper and dependencies
image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "openai-whisper==20231117",
        "numpy==1.26.0",
        "torch==2.1.0",
        "ffmpeg-python==0.2.0",
    )
    .apt_install("ffmpeg")
)

# Configure GPU (T4 is cost-effective for Whisper)
GPU_CONFIG = modal.gpu.T4()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.function(
    image=image,
    gpu=GPU_CONFIG,
    timeout=600,
    container_idle_timeout=120,
    allow_concurrent_inputs=10,
)
@modal.web_endpoint(method="GET")
async def transcribe_websocket(request):
    """WebSocket endpoint for real-time audio transcription."""
    import whisper
    from starlette.websockets import WebSocket

    # Load Whisper model (cached after first load)
    model_name = "base.en"
    logger.info(f"Loading Whisper model: {model_name}")
    model = whisper.load_model(model_name)
    logger.info("Model loaded successfully")

    # Accept WebSocket connection
    websocket = WebSocket(request.scope, receive=request.receive, send=request._send)
    await websocket.accept()

    audio_buffer = []
    connections_count = 0

    try:
        logger.info("WebSocket connection established")
        connections_count += 1

        async for message in websocket.iter_bytes():
            try:
                # Receive binary audio chunk
                audio_chunk = np.frombuffer(message, dtype=np.float32)
                audio_buffer.append(audio_chunk)

                # Send partial transcript every 16 chunks (~1 second at 16kHz)
                if len(audio_buffer) >= 16:
                    audio = np.concatenate(audio_buffer)

                    # Transcribe with Whisper
                    result = model.transcribe(
                        audio, language="en", task="transcribe", fp16=False
                    )

                    await websocket.send_json(
                        {
                            "type": "partial",
                            "text": result["text"].strip(),
                            "timestamp": asyncio.get_event_loop().time(),
                        }
                    )

                    # Keep last few chunks for context
                    audio_buffer = audio_buffer[-8:]

            except Exception as e:
                logger.error(f"Error processing audio chunk: {e}")
                await websocket.send_json(
                    {"type": "error", "message": str(e), "code": "PROCESSING_ERROR"}
                )

        # Connection closed by client, send final transcript
        if audio_buffer:
            audio = np.concatenate(audio_buffer)
            result = model.transcribe(audio, language="en", task="transcribe", fp16=False)

            await websocket.send_json(
                {
                    "type": "final",
                    "text": result["text"].strip(),
                    "confidence": 0.95,
                    "timestamp": asyncio.get_event_loop().time(),
                }
            )

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json(
                {"type": "error", "message": str(e), "code": "INTERNAL_ERROR"}
            )
        except:
            pass
    finally:
        connections_count -= 1
        logger.info(f"WebSocket connection closed. Active connections: {connections_count}")
        await websocket.close()


@app.function(image=image)
@modal.web_endpoint(method="GET")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "voicedform-whisper"}


# For local testing
@app.local_entrypoint()
def main():
    """Test the Whisper service locally."""
    print("Whisper service is configured for Modal deployment")
    print("Deploy with: modal deploy whisper_server.py")
    print("After deployment, get your WebSocket URL from Modal dashboard")
