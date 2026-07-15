# VoicedForm 🎙️

> Voice-driven form completion powered by LangGraph and OpenAI Whisper

[![CI](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/unit-tests.yml)
[![Integration Tests](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/integration-tests.yml/badge.svg)](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/integration-tests.yml)

VoicedForm is an intelligent voice-driven form completion system built with [LangGraph](https://github.com/langchain-ai/langgraph). It uses AI agents to help users complete forms through natural conversational interaction - either by voice or text.

## Features

- **Voice Input**: Transcribe speech to text using OpenAI Whisper on Modal
- **Intelligent Form Detection**: Automatically determines form type from user input
- **AI-Powered Completion**: Uses GPT-4 to extract and organize form data
- **LangGraph Workflow**: Multi-node workflow with supervisor pattern
- **Serverless Deployment**: Whisper runs on Modal's GPU infrastructure
- **Flexible Input**: Supports both voice and text input

## Architecture

```
┌─────────────┐
│ User Input  │
│ (Voice/Text)│
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ Audio            │
│ Transcription    │  ← Whisper on Modal
└────────┬─────────┘
         │
         ▼
┌────────────────────────────────────────┐
│          LangGraph Workflow            │
│  ┌──────────┐  ┌──────────────┐       │
│  │Supervisor│→ │Form Selector │       │
│  └──────────┘  └──────┬───────┘       │
│                       │                │
│  ┌──────────────┐  ┌─▼──────────┐     │
│  │  Validator   │← │Form Complete│     │
│  └──────────────┘  └────────────┘     │
└────────────────────────────────────────┘
         │
         ▼
┌──────────────────┐
│ Completed Form   │
└──────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
# Clone repository
git clone https://github.com/jojopeligroso/VoicedForm.git
cd VoicedForm

# Install Python dependencies
pip install -e .
pip install modal httpx

# Authenticate with Modal
modal setup
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API keys
# OPENAI_API_KEY=sk-...
# WHISPER_API_URL=<will be set after Modal deployment>
```

### 3. Deploy Whisper Server

```bash
# Deploy to Modal (first time)
modal deploy modal_whisper_server.py

# Copy the Web endpoint URL and add to .env
# WHISPER_API_URL=https://your-workspace--voicedform-whisper-fastapi-app.modal.run
```

### 4. Run VoicedForm

```bash
# Run with voice input
python voicedform_graph_with_audio.py your_audio_file.mp3

# Or run with text input
python voicedform_graph_with_audio.py
```

## Project Structure

```
VoicedForm/
├── modal_whisper_server.py           # Whisper server on Modal
├── src/
│   ├── agent/                        # LangGraph agent template
│   └── whisper_client.py             # Whisper API client
├── voicedform_graph.py               # Original graph (text only)
├── voicedform_graph_with_audio.py    # Enhanced graph with audio
├── examples/
│   └── whisper_usage_examples.py     # Usage examples
├── tests/
│   ├── unit_tests/                   # Unit tests
│   ├── integration_tests/            # Integration tests
│   └── test_whisper_integration.py   # Whisper tests
├── WHISPER_README.md                 # Whisper integration docs
├── WHISPER_DEPLOYMENT.md             # Deployment guide
└── README.md                         # This file
```

## Usage

### Voice Input Example

```python
from voicedform_graph_with_audio import process_voice_input

# Process voice recording
result = process_voice_input("accident_report.mp3")

print(f"Transcribed: {result['transcribed_text']}")
print(f"Form Type: {result['form_type']}")
print(f"Completed Form:\n{result['form_complete']}")
```

### Text Input Example

```python
from voicedform_graph_with_audio import process_text_input

# Process text directly
result = process_text_input(
    "I need to report an accident on Main Street today at 2pm"
)

print(f"Form Type: {result['form_type']}")
print(f"Completed Form:\n{result['form_complete']}")
```

### Using Whisper Client Directly

```python
from src.whisper_client import WhisperClient

client = WhisperClient()
result = client.transcribe("audio.mp3", language="en")

if result.success:
    print(f"Transcription: {result.text}")
    print(f"Language: {result.language}")
```

## Documentation

- **[WHISPER_README.md](WHISPER_README.md)** - Whisper integration overview and API reference
- **[WHISPER_DEPLOYMENT.md](WHISPER_DEPLOYMENT.md)** - Comprehensive deployment guide
- **[examples/whisper_usage_examples.py](examples/whisper_usage_examples.py)** - 10+ usage examples

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run unit tests
pytest tests/unit_tests -v

# Run integration tests
pytest tests/integration_tests -v

# Run Whisper integration tests
pytest tests/test_whisper_integration.py -v
```

### Development with LangGraph Studio

```bash
# Start LangGraph dev server
langgraph dev
```

Open [LangGraph Studio](https://langchain-ai.github.io/langgraph/concepts/langgraph_studio/) to visualize and debug your workflow.

### Hot Reload

Local changes to graph files are automatically applied via hot reload while LangGraph Studio is running.

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4 | Yes |
| `WHISPER_API_URL` | Modal Whisper API endpoint | Yes |
| `LANGSMITH_PROJECT` | LangSmith project name | No |
| `LANGCHAIN_TRACING_V2` | Enable LangSmith tracing | No |
| `LANGCHAIN_API_KEY` | LangSmith API key | No |

### Whisper Configuration

Edit `modal_whisper_server.py` to customize:

```python
# Model size (tiny, base, small, medium, large)
model_size: str = "base"

# GPU type (affects cost and speed)
GPU_CONFIG = modal.gpu.A10G()

# Container timeout (affects cost)
container_idle_timeout=300  # 5 minutes
```

## How It Works

### 1. Audio Transcription (Optional)

If audio input is provided, the Whisper Modal server transcribes it to text:

```python
def audio_transcription_node(state):
    result = whisper_client.transcribe(state["audio_file"])
    return {"transcribed_text": result.text, "user_input": result.text}
```

### 2. Supervisor

Analyzes user input to determine form type:

```python
def supervisor_node(state):
    form_type = llm.invoke(f"Determine form type for: {state['user_input']}")
    return {"form_type": form_type}
```

### 3. Form Selector

Identifies required fields for the form:

```python
def form_selector_node(state):
    fields = llm.invoke(f"List required fields for {state['form_type']}")
    return {"form_fields": fields}
```

### 4. Form Completion

Extracts data from user input and populates form:

```python
def form_completion_node(state):
    completed = llm.invoke(f"Fill form with: {state['user_input']}")
    return {"form_complete": completed}
```

### 5. Validator

Verifies form is properly completed:

```python
def validator_node(state):
    is_valid = check_form_complete(state["form_complete"])
    return {"valid": is_valid}
```

## Deployment

### Modal Deployment

```bash
# Development deployment (with live reload)
modal serve modal_whisper_server.py

# Production deployment
modal deploy modal_whisper_server.py
```

### Cost Estimation

Based on typical usage (100 transcriptions/day, 1 min each, base model):

- **GPU Time**: ~$0.13/day
- **Storage**: <$0.10/month
- **Monthly Total**: ~$5-10

See [WHISPER_DEPLOYMENT.md](WHISPER_DEPLOYMENT.md) for detailed cost optimization strategies.

## Examples

See [examples/whisper_usage_examples.py](examples/whisper_usage_examples.py) for comprehensive examples including:

1. Basic transcription
2. Language specification
3. Different model sizes
4. Translation to English
5. Context-aware transcription
6. Segment-level analysis
7. Async transcription
8. Error handling
9. VoicedForm integration

## Troubleshooting

### Common Issues

**"No API URL configured"**
```bash
export WHISPER_API_URL="https://your-modal-url.modal.run"
```

**"Modal authentication failed"**
```bash
modal setup
```

**Slow transcription**
- Use smaller model (`model_size="tiny"`)
- Specify language (`language="en"`)
- Upgrade GPU (`GPU_CONFIG = modal.gpu.A100()`)

See [WHISPER_DEPLOYMENT.md](WHISPER_DEPLOYMENT.md) for complete troubleshooting guide.

## Performance

| Model | Cold Start | Warm Start | 1 min Audio |
|-------|-----------|------------|-------------|
| tiny  | ~3s       | <100ms     | ~2s         |
| base  | ~4s       | <100ms     | ~4s         |
| small | ~6s       | <100ms     | ~8s         |
| medium| ~10s      | <100ms     | ~15s        |
| large | ~15s      | <100ms     | ~30s        |

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## Resources

- **[LangGraph Documentation](https://langchain-ai.github.io/langgraph/)**
- **[Modal Documentation](https://modal.com/docs)**
- **[OpenAI Whisper](https://github.com/openai/whisper)**
- **[LangGraph Studio](https://langchain-ai.github.io/langgraph/concepts/langgraph_studio/)**
- **[LangSmith](https://smith.langchain.com/)**

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph)
- Powered by [OpenAI Whisper](https://github.com/openai/whisper)
- Deployed on [Modal](https://modal.com)
- Based on LangChain's [new-langgraph-project](https://github.com/langchain-ai/new-langgraph-project) template

## Support

- **Issues**: [GitHub Issues](https://github.com/jojopeligroso/VoicedForm/issues)
- **Discussions**: [GitHub Discussions](https://github.com/jojopeligroso/VoicedForm/discussions)
- **Documentation**: See `WHISPER_DEPLOYMENT.md` and `WHISPER_README.md`

---

Made with ❤️ by the VoicedForm team
