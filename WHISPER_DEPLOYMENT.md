# Whisper Deployment Guide for VoicedForm

This guide covers everything you need to deploy and use the Modal Whisper server for speech-to-text transcription in VoicedForm.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Deployment Steps](#deployment-steps)
- [Usage](#usage)
- [Configuration](#configuration)
- [Testing](#testing)
- [Monitoring & Debugging](#monitoring--debugging)
- [Cost Optimization](#cost-optimization)
- [Troubleshooting](#troubleshooting)

## Overview

The VoicedForm Whisper integration provides serverless speech-to-text capabilities using:

- **Modal**: Serverless GPU infrastructure for running Whisper
- **OpenAI Whisper**: State-of-the-art speech recognition model
- **FastAPI**: REST API for easy integration
- **LangGraph**: Integration with form completion workflow

### Architecture

```
┌─────────────┐
│ User Audio  │
└──────┬──────┘
       │
       ▼
┌──────────────────────┐
│  VoicedForm Client   │
│  (whisper_client.py) │
└──────┬───────────────┘
       │ HTTP/gRPC
       ▼
┌──────────────────────┐
│  Modal Whisper API   │
│  (GPU-accelerated)   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ LangGraph Workflow   │
│ (Form Completion)    │
└──────────────────────┘
```

## Prerequisites

### 1. Modal Account

Sign up for a Modal account at https://modal.com

```bash
# Install Modal CLI
pip install modal

# Authenticate (opens browser)
modal setup
```

### 2. Python Environment

- Python 3.9 or higher
- pip or uv package manager

### 3. Required API Keys

- **Modal Token**: Automatically configured via `modal setup`
- **OpenAI API Key**: For LangGraph workflow (optional for Whisper only)

## Quick Start

### 1. Install Dependencies

```bash
# Using pip
pip install modal httpx python-dotenv

# Using uv (recommended)
uv pip install modal httpx python-dotenv
```

### 2. Deploy to Modal

```bash
# Deploy the Whisper server
modal deploy modal_whisper_server.py

# You'll see output like:
# ✓ Created deployment d-1234567890
# View deployment: https://modal.com/apps/your-workspace/voicedform-whisper
#
# Web endpoint: https://your-workspace--voicedform-whisper-fastapi-app.modal.run
```

### 3. Configure Environment

```bash
# Copy the web endpoint URL from deployment output
export WHISPER_API_URL="https://your-workspace--voicedform-whisper-fastapi-app.modal.run"

# Or add to .env file
echo "WHISPER_API_URL=https://your-workspace--voicedform-whisper-fastapi-app.modal.run" >> .env
```

### 4. Test the Deployment

```bash
# Test with a sample audio file
python -c "
from src.whisper_client import transcribe
result = transcribe('test_audio.mp3')
print(result.text)
"
```

## Deployment Steps

### Step 1: Deploy the Modal Server

The Modal server hosts the Whisper model and provides API endpoints.

```bash
# Deploy to production
modal deploy modal_whisper_server.py

# Or run in development mode (with live reloading)
modal serve modal_whisper_server.py
```

**Deployment options:**

- `modal deploy`: Production deployment (persistent)
- `modal serve`: Development deployment (stops when you exit)
- `modal run`: Run once and exit (for testing)

### Step 2: Get Your API URL

After deployment, Modal will output your API URL:

```
Web endpoint: https://USERNAME--voicedform-whisper-fastapi-app.modal.run
```

### Step 3: Configure Your Application

Add the API URL to your environment:

**Option A: `.env` file (recommended)**

```bash
# .env
WHISPER_API_URL=https://USERNAME--voicedform-whisper-fastapi-app.modal.run
OPENAI_API_KEY=sk-...
LANGSMITH_PROJECT=voicedform
```

**Option B: Environment variables**

```bash
export WHISPER_API_URL="https://USERNAME--voicedform-whisper-fastapi-app.modal.run"
```

### Step 4: Verify Deployment

```bash
# Check health endpoint
curl https://USERNAME--voicedform-whisper-fastapi-app.modal.run/health

# Expected response:
# {"status":"healthy","service":"whisper-api"}
```

## Usage

### Basic Transcription

```python
from src.whisper_client import WhisperClient

# Initialize client
client = WhisperClient()

# Transcribe audio file
result = client.transcribe("audio.mp3")

if result.success:
    print(f"Transcription: {result.text}")
    print(f"Language: {result.language}")
else:
    print(f"Error: {result.error}")
```

### Advanced Options

```python
# Specify language (faster than auto-detect)
result = client.transcribe(
    "audio.mp3",
    language="en",  # English
    model_size="small",  # Use small model
)

# Translate to English
result = client.transcribe(
    "audio.mp3",
    task="translate",  # Translate to English
)

# Guide transcription with context
result = client.transcribe(
    "audio.mp3",
    initial_prompt="Form completion for accident report",
    temperature=0.0,  # Deterministic output
)
```

### Integration with VoicedForm Workflow

```python
from voicedform_graph_with_audio import process_voice_input, process_text_input

# Process voice input
result = process_voice_input("user_recording.mp3")
print(result["form_complete"])

# Process text input (no transcription)
result = process_text_input("I need to report an accident")
print(result["form_complete"])
```

### Async Usage

```python
import asyncio
from src.whisper_client import WhisperClient

async def transcribe_async():
    client = WhisperClient()
    result = await client.transcribe_async("audio.mp3")
    return result.text

# Run async
text = asyncio.run(transcribe_async())
```

### HTTP API Usage

You can also call the API directly with curl or any HTTP client:

```bash
# Transcribe audio file
curl -X POST \
  https://USERNAME--voicedform-whisper-fastapi-app.modal.run/transcribe \
  -F "audio=@audio.mp3" \
  -F "model_size=base" \
  -F "language=en"

# Response:
# {
#   "text": "This is the transcribed text",
#   "language": "en",
#   "segments": [...],
#   "model_size": "base"
# }
```

## Configuration

### Whisper Model Sizes

Choose the model size based on your accuracy vs. speed requirements:

| Model  | Parameters | Speed    | Accuracy | Use Case                    |
|--------|------------|----------|----------|-----------------------------|
| tiny   | 39M        | Fastest  | Low      | Real-time, low accuracy OK  |
| base   | 74M        | Fast     | Good     | **Recommended for most**    |
| small  | 244M       | Medium   | Better   | Higher accuracy needed      |
| medium | 769M       | Slow     | Great    | Critical accuracy           |
| large  | 1550M      | Slowest  | Best     | Maximum accuracy            |

**Recommendation**: Start with `base` for the best balance of speed and accuracy.

### Environment Variables

| Variable           | Description                              | Required | Default                    |
|-------------------|------------------------------------------|----------|----------------------------|
| `WHISPER_API_URL` | Modal Whisper API endpoint               | Yes      | None                       |
| `OPENAI_API_KEY`  | OpenAI API key for LangGraph             | Yes*     | None                       |
| `LANGSMITH_PROJECT` | LangSmith project for tracing          | No       | "voicedform"               |

*Required only for full VoicedForm workflow, not for Whisper-only usage.

### Modal Configuration

Edit `modal_whisper_server.py` to customize:

```python
# GPU type (affects cost and speed)
GPU_CONFIG = modal.gpu.A10G()  # Options: T4, A10G, A100

# Container timeout (affects cost)
container_idle_timeout=300,  # Keep warm for 5 minutes

# Model cache volume
model_cache = modal.Volume.from_name("whisper-model-cache", create_if_missing=True)
```

## Testing

### 1. Test Modal Deployment Directly

```bash
# Test with CLI (requires audio file)
modal run modal_whisper_server.py --audio-file test_audio.mp3 --model-size base
```

### 2. Test Python Client

```python
# test_whisper.py
from src.whisper_client import WhisperClient

def test_transcription():
    client = WhisperClient()

    # Test with sample audio
    result = client.transcribe("test_audio.mp3")

    assert result.success, f"Transcription failed: {result.error}"
    assert len(result.text) > 0, "Empty transcription"
    print(f"✓ Transcription: {result.text}")

if __name__ == "__main__":
    test_transcription()
    print("✓ All tests passed!")
```

### 3. Test Full Workflow

```bash
# Run VoicedForm with audio input
python voicedform_graph_with_audio.py test_audio.mp3
```

### 4. Test API Health

```python
from src.whisper_client import WhisperClient

client = WhisperClient()
if client.health_check():
    print("✓ Whisper API is healthy")
else:
    print("✗ Whisper API is not accessible")
```

## Monitoring & Debugging

### Modal Dashboard

View logs and metrics at: https://modal.com/apps

- **Logs**: Real-time function execution logs
- **Metrics**: Request count, duration, errors
- **Costs**: GPU usage and billing

### Enable Debug Logging

```python
# In modal_whisper_server.py, add print statements
print(f"Transcribing {len(audio_data)} bytes...")
print(f"Result: {result['text']}")
```

### LangSmith Tracing (Optional)

Enable LangSmith for end-to-end tracing:

```bash
# .env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=voicedform
```

View traces at: https://smith.langchain.com

### Common Debug Commands

```bash
# View Modal logs in real-time
modal logs voicedform-whisper

# View recent deployments
modal app list

# Get deployment details
modal app describe voicedform-whisper
```

## Cost Optimization

### 1. Choose the Right GPU

```python
# Cost-effective for most cases
GPU_CONFIG = modal.gpu.T4()  # ~$0.60/hour

# Recommended balance
GPU_CONFIG = modal.gpu.A10G()  # ~$1.20/hour

# High performance (expensive)
GPU_CONFIG = modal.gpu.A100()  # ~$4.00/hour
```

### 2. Adjust Container Timeout

```python
# Shorter timeout = lower cost, but more cold starts
container_idle_timeout=120,  # 2 minutes

# Longer timeout = higher cost, but faster response
container_idle_timeout=600,  # 10 minutes
```

### 3. Use Smaller Models When Possible

```python
# For testing/development
model_size = "tiny"  # Fastest, cheapest

# For production
model_size = "base"  # Good balance
```

### 4. Batch Processing

```python
# Process multiple files in one request to amortize cold start
for audio_file in audio_files:
    result = client.transcribe(audio_file)
```

### Estimated Costs

Based on Modal pricing (as of 2024):

- **GPU time**: ~$0.60-$4.00/hour depending on GPU type
- **Idle time**: Charged when container is kept warm
- **Storage**: ~$0.10/GB/month for model cache

**Example**:
- 100 transcriptions/day
- Average 30 seconds each
- Base model on A10G GPU
- Cost: ~$5-10/month

## Troubleshooting

### Issue: "No API URL configured"

**Solution**: Set the `WHISPER_API_URL` environment variable:

```bash
export WHISPER_API_URL="https://your-url.modal.run"
# Or add to .env file
```

### Issue: "Modal package not installed"

**Solution**: Install Modal:

```bash
pip install modal
```

### Issue: "Authentication failed"

**Solution**: Re-authenticate with Modal:

```bash
modal setup
```

### Issue: "GPU out of memory"

**Solution**: Use a smaller model or upgrade GPU:

```python
# Option 1: Smaller model
model_size = "small"  # Instead of "large"

# Option 2: Bigger GPU
GPU_CONFIG = modal.gpu.A100()
```

### Issue: "Transcription timeout"

**Solution**: Increase timeout or split audio:

```python
# Increase timeout
timeout=1200,  # 20 minutes

# Or split long audio files
# Use pydub or ffmpeg to split audio into chunks
```

### Issue: "Cold start is too slow"

**Solution**: Keep containers warm longer:

```python
container_idle_timeout=600,  # 10 minutes instead of 5
```

### Issue: "Incorrect transcription"

**Solutions**:

1. **Use larger model**: `model_size="medium"`
2. **Specify language**: `language="en"` instead of auto-detect
3. **Add context**: `initial_prompt="Medical terminology, accident report"`
4. **Check audio quality**: Ensure clear audio, minimal background noise

### Getting Help

- **Modal Docs**: https://modal.com/docs
- **Whisper Docs**: https://github.com/openai/whisper
- **Issues**: Open an issue on the VoicedForm repository

## Next Steps

- [ ] Deploy to production with `modal deploy`
- [ ] Test with real audio samples
- [ ] Integrate with your form completion workflow
- [ ] Set up monitoring and alerts
- [ ] Optimize model size and GPU type for your use case
- [ ] Implement batch processing for multiple files

## Additional Resources

- [Modal Documentation](https://modal.com/docs)
- [OpenAI Whisper Repository](https://github.com/openai/whisper)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [VoicedForm GitHub](https://github.com/jojopeligroso/VoicedForm)
