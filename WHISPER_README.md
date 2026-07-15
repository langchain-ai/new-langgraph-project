# Whisper Integration for VoicedForm

> Voice-driven form completion powered by OpenAI Whisper on Modal

## Overview

This integration adds speech-to-text capabilities to VoicedForm using OpenAI's Whisper model deployed on Modal's serverless GPU infrastructure. Users can now complete forms using voice input instead of typing.

## Features

- **High-Quality Transcription**: OpenAI Whisper provides state-of-the-art speech recognition
- **Serverless Deployment**: Modal handles GPU provisioning and scaling automatically
- **Multiple Model Sizes**: Choose from tiny to large models based on your accuracy needs
- **REST API**: Easy integration via HTTP endpoints
- **LangGraph Integration**: Seamlessly works with existing VoicedForm workflow
- **Multi-language Support**: Automatic language detection and translation to English
- **Cost-Effective**: Pay only for actual transcription time, not idle GPU time

## Quick Start

### 1. Install Dependencies

```bash
pip install modal httpx python-dotenv
```

### 2. Deploy Whisper Server

```bash
# Authenticate with Modal
modal setup

# Deploy the server
modal deploy modal_whisper_server.py
```

### 3. Configure Environment

Copy the API URL from deployment output and add to `.env`:

```bash
WHISPER_API_URL=https://your-workspace--voicedform-whisper-fastapi-app.modal.run
OPENAI_API_KEY=sk-your-openai-key
```

### 4. Test Transcription

```python
from src.whisper_client import transcribe

result = transcribe("audio.mp3")
print(result.text)
```

## Architecture

```
┌──────────────┐
│ Audio Input  │
└──────┬───────┘
       │
       ▼
┌─────────────────────┐
│  WhisperClient      │  (src/whisper_client.py)
│  - HTTP/gRPC        │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  Modal Whisper API  │  (modal_whisper_server.py)
│  - GPU-accelerated  │
│  - FastAPI          │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  OpenAI Whisper     │
│  - Model inference  │
└─────────────────────┘
```

## File Structure

```
VoicedForm/
├── modal_whisper_server.py           # Modal server implementation
├── src/
│   └── whisper_client.py             # Python client for Whisper API
├── voicedform_graph_with_audio.py    # Enhanced workflow with audio
├── examples/
│   └── whisper_usage_examples.py     # Usage examples
├── tests/
│   └── test_whisper_integration.py   # Integration tests
├── WHISPER_DEPLOYMENT.md             # Detailed deployment guide
└── WHISPER_README.md                 # This file
```

## Usage Examples

### Basic Transcription

```python
from src.whisper_client import WhisperClient

client = WhisperClient()
result = client.transcribe("audio.mp3")

if result.success:
    print(f"Text: {result.text}")
    print(f"Language: {result.language}")
```

### Specify Language (Faster)

```python
# Specifying language improves speed and accuracy
result = client.transcribe("audio.mp3", language="en")
```

### Use Different Model Sizes

```python
# Tiny model - fastest, lowest accuracy
client = WhisperClient(model_size="tiny")

# Base model - good balance (recommended)
client = WhisperClient(model_size="base")

# Large model - best accuracy, slower
client = WhisperClient(model_size="large")
```

### Translate to English

```python
# Automatically translate to English
result = client.transcribe(
    "spanish_audio.mp3",
    task="translate"
)
```

### Integration with VoicedForm

```python
from voicedform_graph_with_audio import process_voice_input

# Process voice through complete workflow
result = process_voice_input("accident_report_recording.mp3")

print(f"Transcribed: {result['transcribed_text']}")
print(f"Form Type: {result['form_type']}")
print(f"Completed: {result['form_complete']}")
```

### Async Transcription

```python
import asyncio

async def transcribe_multiple():
    client = WhisperClient()

    results = await asyncio.gather(
        client.transcribe_async("file1.mp3"),
        client.transcribe_async("file2.mp3"),
        client.transcribe_async("file3.mp3"),
    )

    for result in results:
        print(result.text)

asyncio.run(transcribe_multiple())
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `WHISPER_API_URL` | Modal Whisper API endpoint | Yes |
| `OPENAI_API_KEY` | OpenAI API key for LangGraph | Yes* |

*Required for full VoicedForm workflow, not for Whisper-only usage

### Model Sizes

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| tiny | 39M | Fastest | Low | Real-time, low accuracy OK |
| base | 74M | Fast | Good | **Recommended default** |
| small | 244M | Medium | Better | Higher accuracy needed |
| medium | 769M | Slow | Great | Critical accuracy |
| large | 1550M | Slowest | Best | Maximum quality |

### GPU Options

Edit `modal_whisper_server.py` to change GPU type:

```python
# Cost-effective
GPU_CONFIG = modal.gpu.T4()  # ~$0.60/hour

# Recommended
GPU_CONFIG = modal.gpu.A10G()  # ~$1.20/hour

# High performance
GPU_CONFIG = modal.gpu.A100()  # ~$4.00/hour
```

## API Reference

### WhisperClient

```python
class WhisperClient:
    def __init__(
        self,
        api_url: Optional[str] = None,
        model_size: str = "base",
        use_direct_modal: bool = False,
    )

    def transcribe(
        self,
        audio: Union[str, Path, bytes],
        language: Optional[str] = None,
        task: str = "transcribe",
        temperature: float = 0.0,
        initial_prompt: Optional[str] = None,
        model_size: Optional[str] = None,
    ) -> WhisperTranscriptionResult

    async def transcribe_async(...) -> WhisperTranscriptionResult

    def health_check(self) -> bool
```

### WhisperTranscriptionResult

```python
class WhisperTranscriptionResult:
    text: str                    # Transcribed text
    language: str                # Detected language
    segments: List[dict]         # Segments with timing
    model_size: str              # Model used
    error: Optional[str]         # Error message if failed
    success: bool                # True if successful
```

### REST API Endpoints

#### `POST /transcribe`

Transcribe audio file to text.

**Parameters:**
- `audio` (file): Audio file to transcribe
- `model_size` (string): Model size (tiny/base/small/medium/large)
- `language` (string, optional): ISO language code
- `task` (string): 'transcribe' or 'translate'
- `temperature` (float): Sampling temperature (0.0-1.0)
- `initial_prompt` (string, optional): Context for transcription

**Response:**
```json
{
  "text": "Transcribed text here",
  "language": "en",
  "segments": [
    {"text": "Segment 1", "start": 0.0, "end": 2.5}
  ],
  "model_size": "base"
}
```

#### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "whisper-api"
}
```

## Testing

### Run Integration Tests

```bash
# Install pytest
pip install pytest pytest-asyncio

# Run tests
pytest tests/test_whisper_integration.py -v
```

### Run Examples

```bash
# Run all usage examples
python examples/whisper_usage_examples.py

# Test with your own audio file
python voicedform_graph_with_audio.py your_audio.mp3
```

### Test Deployment

```bash
# Test Modal deployment directly
modal run modal_whisper_server.py --audio-file test.mp3
```

## Deployment

See [WHISPER_DEPLOYMENT.md](WHISPER_DEPLOYMENT.md) for comprehensive deployment guide covering:

- Prerequisites and setup
- Step-by-step deployment instructions
- Configuration options
- Monitoring and debugging
- Cost optimization strategies
- Troubleshooting common issues

## Performance

### Typical Latency

| Model | Cold Start | Warm Start | Transcription (1 min audio) |
|-------|-----------|------------|---------------------------|
| tiny | ~3s | <100ms | ~2s |
| base | ~4s | <100ms | ~4s |
| small | ~6s | <100ms | ~8s |
| medium | ~10s | <100ms | ~15s |
| large | ~15s | <100ms | ~30s |

### Optimization Tips

1. **Keep containers warm**: Increase `container_idle_timeout`
2. **Specify language**: Faster than auto-detection
3. **Use base model**: Best balance for most use cases
4. **Batch processing**: Process multiple files in sequence

## Cost Estimation

Based on Modal pricing (2024):

**Example Usage:**
- 100 transcriptions per day
- Average 1 minute audio per file
- Base model on A10G GPU
- 5 minute container idle timeout

**Monthly Cost:** ~$5-10

**Cost Breakdown:**
- GPU time: ~$1.20/hour × (100 × 4s / 3600) = ~$0.13/day
- Idle time: Depends on traffic pattern
- Storage: <$0.10/month for model cache

## Troubleshooting

### Common Issues

**"No API URL configured"**
```bash
export WHISPER_API_URL="your-modal-url"
```

**"Modal package not installed"**
```bash
pip install modal
```

**"Authentication failed"**
```bash
modal setup
```

**Slow transcription**
- Use smaller model (tiny or base)
- Specify language instead of auto-detect
- Split long audio files

**Low accuracy**
- Use larger model (medium or large)
- Add context via `initial_prompt`
- Ensure audio quality is good

See [WHISPER_DEPLOYMENT.md](WHISPER_DEPLOYMENT.md) for more troubleshooting help.

## Support

- **Documentation**: See `WHISPER_DEPLOYMENT.md`
- **Examples**: See `examples/whisper_usage_examples.py`
- **Tests**: See `tests/test_whisper_integration.py`
- **Modal Docs**: https://modal.com/docs
- **Whisper Docs**: https://github.com/openai/whisper

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please:

1. Test your changes with `pytest`
2. Follow existing code style
3. Update documentation as needed
4. Add examples for new features

## Changelog

### v1.0.0 (2024)

- Initial Whisper integration
- Modal serverless deployment
- Python client library
- LangGraph workflow integration
- Comprehensive documentation
- Example code and tests
