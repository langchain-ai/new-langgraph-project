# Whisper WebSocket Service - Modal Deployment

Real-time speech-to-text transcription service for VoicedForm, deployed on Modal.com with GPU acceleration.

## Why Modal?

Modal provides:
- **Serverless GPU**: Automatic scaling with GPU (T4) for Whisper
- **WebSocket Support**: Native WebSocket endpoints
- **Cold Start Optimization**: Model caching between invocations
- **Cost Effective**: Pay only for actual usage

## Prerequisites

1. **Modal Account**: Sign up at [modal.com](https://modal.com)
2. **Python 3.9+**: For local Modal CLI
3. **Modal CLI**: Install via `pip install modal`

## Setup Instructions

### 1. Install Modal CLI

```bash
pip install modal
```

### 2. Authenticate with Modal

```bash
modal token new
```

This will open a browser window to authenticate. Follow the prompts to create/link your Modal account.

### 3. Deploy the Whisper Service

```bash
cd whisper-service
modal deploy whisper_server.py
```

The deployment process will:
- Build a container image with Whisper, PyTorch, and dependencies
- Deploy the WebSocket endpoint with GPU support
- Cache the Whisper model for fast cold starts

### 4. Get Your WebSocket URL

After deployment, Modal will output your endpoint URL:

```
✓ Created web function transcribe_websocket => https://your-workspace--voicedform-whisper-transcribe-websocket.modal.run
```

Copy this URL and convert it to WebSocket format:
```
https://... → wss://...
```

### 5. Configure Environment Variable

Add to your `.env.local` in the `web/` directory:

```bash
WHISPER_WS_URL=wss://your-workspace--voicedform-whisper-transcribe-websocket.modal.run
```

## Configuration Options

### Model Selection

Edit `whisper_server.py` to change the Whisper model:

```python
model_name = "tiny.en"    # Fastest, lowest quality
model_name = "base.en"    # Balanced (default)
model_name = "small.en"   # Better quality
model_name = "medium.en"  # High quality, slower
```

### GPU Configuration

Change GPU type in `whisper_server.py`:

```python
GPU_CONFIG = modal.gpu.T4()      # Cost-effective (default)
GPU_CONFIG = modal.gpu.A10G()    # Faster
GPU_CONFIG = modal.gpu.A100()    # Highest performance
```

### Scaling Settings

Adjust concurrent connections:

```python
@app.function(
    allow_concurrent_inputs=10,  # Max concurrent WebSocket connections
    timeout=600,                  # Max connection duration (seconds)
    container_idle_timeout=120,   # How long to keep container warm
)
```

## Testing the Service

### 1. Health Check

```bash
curl https://your-workspace--voicedform-whisper-health.modal.run
```

Expected response:
```json
{"status": "healthy", "service": "voicedform-whisper"}
```

### 2. WebSocket Test

Use a WebSocket client to test:

```javascript
const ws = new WebSocket('wss://your-workspace--voicedform-whisper-transcribe-websocket.modal.run')

ws.onopen = () => {
  console.log('Connected to Whisper service')
  // Send audio chunks as Float32Array
}

ws.onmessage = (event) => {
  const data = JSON.parse(event.data)
  console.log('Transcript:', data.text)
}
```

### 3. Test with VoicedForm App

1. Start your Next.js app: `npm run dev`
2. Sign in and start a form
3. Enable microphone when prompted
4. Speak into your microphone
5. Watch real-time transcription appear

## Monitoring & Debugging

### View Logs

```bash
modal app logs voicedform-whisper
```

### Check Usage

Visit [modal.com/apps](https://modal.com/apps) to see:
- Request count
- Compute time
- Costs
- Error rates

### Update Deployment

After code changes:

```bash
modal deploy whisper_server.py
```

Changes are live immediately with zero downtime.

## Cost Estimation

Modal pricing (as of 2024):
- **T4 GPU**: ~$0.60/hour
- **CPU**: Minimal cost
- **Network**: Free for first 10GB

Example usage:
- 100 forms/day × 5 minutes each = ~8.3 hours/month
- Estimated cost: ~$5-10/month with T4 GPU

Cold starts are optimized, so you only pay for active transcription time.

## Troubleshooting

### "WebSocket connection failed"

1. Verify URL is correct and uses `wss://` (not `https://`)
2. Check Modal deployment status: `modal app list`
3. View logs: `modal app logs voicedform-whisper`

### "Model loading timeout"

- Increase `timeout` in function decorator
- Consider using a smaller model (tiny.en or base.en)
- Upgrade to faster GPU (A10G)

### "Audio processing error"

- Ensure audio format is Float32Array, 16kHz
- Check browser console for client-side errors
- Verify audio chunks are being sent correctly

### High latency

1. Check your internet connection
2. Consider using a smaller Whisper model
3. Upgrade GPU type (T4 → A10G → A100)
4. Reduce chunk size for more frequent updates

## Production Best Practices

1. **Set up alerts**: Configure Modal to alert on errors
2. **Monitor costs**: Review usage in Modal dashboard weekly
3. **Rate limiting**: Implement per-user rate limits in your app
4. **Graceful fallback**: Allow text input if Whisper is unavailable
5. **Model caching**: Keep containers warm with `container_idle_timeout`

## Advanced Features (Future)

- **Multi-language**: Change `language="en"` to support other languages
- **Custom vocabulary**: Fine-tune Whisper for domain-specific terms
- **Diarization**: Identify multiple speakers
- **Timestamp alignment**: Get word-level timestamps

## Support

- Modal Docs: [modal.com/docs](https://modal.com/docs)
- Whisper Docs: [github.com/openai/whisper](https://github.com/openai/whisper)
- VoicedForm Issues: [Your GitHub repo]

## License

Same as parent project (MIT)
