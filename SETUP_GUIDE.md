# VoicedForm Setup Guide

This guide will help you get VoicedForm up and running with Whisper speech-to-text capabilities in under 10 minutes.

## Prerequisites

Before you begin, ensure you have:

- Python 3.9 or higher
- pip or uv package manager
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))
- Modal account ([sign up here](https://modal.com))

## Step-by-Step Setup

### 1. Clone and Install (2 minutes)

```bash
# Clone the repository
git clone https://github.com/jojopeligroso/VoicedForm.git
cd VoicedForm

# Install dependencies
pip install -e .

# Install Modal and HTTP client
pip install modal httpx
```

### 2. Configure Modal (1 minute)

```bash
# Authenticate with Modal (opens browser)
modal setup
```

Follow the prompts to authenticate. This creates a Modal token in `~/.modal.toml`.

### 3. Deploy Whisper Server (3 minutes)

```bash
# Deploy to Modal
make whisper_deploy

# Or manually:
# modal deploy modal_whisper_server.py
```

You'll see output like:

```
✓ Created deployment d-1234567890
View deployment: https://modal.com/apps/your-workspace/voicedform-whisper

Web endpoint: https://your-workspace--voicedform-whisper-fastapi-app.modal.run
```

**Important**: Copy the `Web endpoint` URL - you'll need it in the next step!

### 4. Configure Environment (1 minute)

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file
nano .env  # or use your preferred editor
```

Add your API keys:

```bash
# Required
OPENAI_API_KEY=sk-your-openai-key-here
WHISPER_API_URL=https://your-workspace--voicedform-whisper-fastapi-app.modal.run

# Optional (for LangSmith tracing)
LANGSMITH_PROJECT=voicedform
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=your-langsmith-key
```

### 5. Test Everything (2 minutes)

```bash
# Test 1: Check Modal deployment
curl https://your-workspace--voicedform-whisper-fastapi-app.modal.run/health

# Expected response: {"status":"healthy","service":"whisper-api"}

# Test 2: Run Whisper integration tests
make whisper_test

# Test 3: Run usage examples
make whisper_examples
```

## Verify Installation

Run this quick verification script:

```python
# verify_setup.py
import os
from dotenv import load_dotenv
from src.whisper_client import WhisperClient

load_dotenv()

print("Checking VoicedForm setup...")
print("-" * 50)

# Check environment variables
openai_key = os.getenv("OPENAI_API_KEY")
whisper_url = os.getenv("WHISPER_API_URL")

print(f"✓ OPENAI_API_KEY: {'Set' if openai_key else 'NOT SET'}")
print(f"✓ WHISPER_API_URL: {'Set' if whisper_url else 'NOT SET'}")

# Check Whisper API health
if whisper_url:
    client = WhisperClient()
    if client.health_check():
        print("✓ Whisper API: Healthy")
    else:
        print("✗ Whisper API: Not accessible")
else:
    print("✗ Whisper API: URL not configured")

print("-" * 50)
print("Setup verification complete!")
```

Run it:

```bash
python verify_setup.py
```

Expected output:

```
Checking VoicedForm setup...
--------------------------------------------------
✓ OPENAI_API_KEY: Set
✓ WHISPER_API_URL: Set
✓ Whisper API: Healthy
--------------------------------------------------
Setup verification complete!
```

## Quick Usage Examples

### Example 1: Transcribe Audio

```python
from src.whisper_client import transcribe

# Simple one-liner
result = transcribe("your_audio.mp3", language="en")
print(result.text)
```

### Example 2: Complete Form with Voice

```python
from voicedform_graph_with_audio import process_voice_input

# Process voice input through full workflow
result = process_voice_input("accident_report.mp3")

print(f"Transcribed: {result['transcribed_text']}")
print(f"Form Type: {result['form_type']}")
print(f"Form:\n{result['form_complete']}")
```

### Example 3: Complete Form with Text

```python
from voicedform_graph_with_audio import process_text_input

# Process text input (no transcription needed)
result = process_text_input(
    "I need to report a car accident on Main Street at 2pm today"
)

print(f"Form:\n{result['form_complete']}")
```

## Common Issues

### Issue: "Modal not found"

**Solution**:
```bash
pip install modal
```

### Issue: "WHISPER_API_URL not set"

**Solution**: Make sure you copied the Web endpoint URL from Modal deployment and added it to `.env`:

```bash
# In .env file
WHISPER_API_URL=https://your-workspace--voicedform-whisper-fastapi-app.modal.run
```

### Issue: "Whisper API not accessible"

**Solution**: Verify deployment is active:

```bash
modal app list
modal app describe voicedform-whisper
```

If not listed, redeploy:

```bash
make whisper_deploy
```

### Issue: "OpenAI API key invalid"

**Solution**: Get a new API key from https://platform.openai.com/api-keys and update `.env`.

### Issue: "Audio file not found"

**Solution**: Provide full path to audio file:

```python
result = transcribe("/full/path/to/audio.mp3")
```

## Next Steps

Now that you're set up, explore:

1. **[WHISPER_README.md](WHISPER_README.md)** - Complete API reference and examples
2. **[WHISPER_DEPLOYMENT.md](WHISPER_DEPLOYMENT.md)** - Advanced deployment options
3. **[examples/whisper_usage_examples.py](examples/whisper_usage_examples.py)** - 10+ usage examples
4. **[tests/test_whisper_integration.py](tests/test_whisper_integration.py)** - Integration tests

## Development Workflow

```bash
# Make code changes
vim voicedform_graph_with_audio.py

# Run tests
make test
make whisper_test

# Deploy updated Whisper server
make whisper_deploy

# Format code
make format

# Lint code
make lint
```

## Getting Help

- **Documentation**: See `WHISPER_README.md` and `WHISPER_DEPLOYMENT.md`
- **Examples**: Run `make whisper_examples`
- **Tests**: Run `make whisper_test`
- **Issues**: https://github.com/jojopeligroso/VoicedForm/issues

## Cost Estimate

With typical usage (100 transcriptions/day, 1 min audio each):

- **Whisper on Modal**: ~$5-10/month
- **OpenAI GPT-4**: Depends on form complexity (~$10-30/month for moderate use)
- **Total**: ~$15-40/month

First-time users get **$30 free credits** on Modal!

## Uninstall

To remove VoicedForm:

```bash
# Delete Modal deployment
modal app delete voicedform-whisper

# Remove Python package
pip uninstall agent

# Delete repository
cd ..
rm -rf VoicedForm
```

---

**Setup complete!** You're ready to use VoicedForm for voice-driven form completion.

For questions or issues, see the [troubleshooting guide](WHISPER_DEPLOYMENT.md#troubleshooting) or [open an issue](https://github.com/jojopeligroso/VoicedForm/issues).
