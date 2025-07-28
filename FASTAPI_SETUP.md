# FastAPI Server Setup and Usage Guide

This guide explains how to set up and run the FastAPI chat server, manage dependencies, and send requests to it.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- OpenAI API key

## 1. Virtual Environment Setup

### Create and Activate Virtual Environment

```bash
# Navigate to project directory
cd /path/to/sappington-langgraph-project

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
# .venv\Scripts\activate
```

### Verify Virtual Environment is Active

You should see `(.venv)` at the beginning of your command prompt:
```bash
(.venv) user@machine:~/sappington-langgraph-project$
```

## 2. Install Dependencies

### Install from requirements.txt
```bash
# Make sure virtual environment is activated
pip install -r requirements.txt
```

### Update requirements.txt with current dependencies
```bash
# Freeze current dependencies to requirements.txt
pip freeze > requirements.txt
```

### Install specific packages if needed
```bash
pip install fastapi uvicorn openai python-dotenv
```

## 3. Environment Configuration

### Create .env file
Create a `.env` file in the project root with your OpenAI API key:

```bash
# Create .env file
echo "OPENAI_API_KEY=your-actual-openai-api-key-here" > .env
```

Or manually create `.env` file with:
```
OPENAI_API_KEY=your-actual-openai-api-key-here
```

**Important:** Replace `your-actual-openai-api-key-here` with your real OpenAI API key.

## 4. Run the Server

### Start the FastAPI server
```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Run the server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Server Options Explained
- `src.main:app` - Points to the FastAPI app instance in `src/main.py`
- `--reload` - Automatically reloads server when code changes (development mode)
- `--host 0.0.0.0` - Makes server accessible from other devices on the network
- `--port 8000` - Runs server on port 8000

### Verify Server is Running
You should see output like:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## 5. API Documentation

### Interactive API Docs
Visit `http://localhost:8000/docs` in your browser to see the interactive FastAPI documentation.

### OpenAPI Schema
Visit `http://localhost:8000/openapi.json` to see the OpenAPI schema.

## 6. Send Requests

### Using curl

#### Basic chat request:
```bash
curl -X POST "http://localhost:8000/chat/test-session" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?",
    "client_id": "user123"
  }'
```

#### Chat request with streaming response:
```bash
curl -X POST "http://localhost:8000/chat/test-session" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is your name?",
    "client_id": "user123"
  }' \
  --no-buffer
```

### Using Python requests

```python
import requests

url = "http://localhost:8000/chat/test-session"
data = {
    "message": "Hello, how are you?",
    "client_id": "user123"
}

# For streaming response
response = requests.post(url, json=data, stream=True)
for chunk in response.iter_content(chunk_size=1024):
    if chunk:
        print(chunk.decode('utf-8'), end='')

# For regular response (not recommended for this streaming API)
# response = requests.post(url, json=data)
# print(response.text)
```

### Using JavaScript/fetch

```javascript
fetch('http://localhost:8000/chat/test-session', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        message: "Hello, how are you?",
        client_id: "user123"
    })
})
.then(response => {
    const reader = response.body.getReader();
    return new ReadableStream({
        start(controller) {
            return pump();
            function pump() {
                return reader.read().then(({done, value}) => {
                    if (done) {
                        controller.close();
                        return;
                    }
                    controller.enqueue(value);
                    return pump();
                });
            }
        }
    });
})
.then(stream => new Response(stream))
.then(response => response.text())
.then(text => console.log(text));
```

## 7. API Endpoints

### POST /chat/{session_id}

**URL Parameters:**
- `session_id` (string): Unique identifier for the chat session

**Request Body:**
```json
{
    "message": "string",     // Required: User's message
    "client_id": "string"    // Required: Unique client identifier
}
```

**Response:**
- Content-Type: `text/plain; charset=utf-8`
- Streaming response with AI-generated text
- Each chunk contains a portion of the AI's response

**Example Response:**
```
Hello! I'm here to help you. I need to gather some information from you. What is your name?
```

## 8. Session Management

- Each `session_id` in the URL can be used for separate conversation contexts
- The `client_id` is used to maintain chat history in the server's memory cache
- Messages persist for the duration of the server session
- The system automatically includes a system prompt to guide the conversation

## 9. Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'utils'**
   - Make sure you're running the server from the project root directory
   - Ensure the virtual environment is activated
   - Check that `src/utils.py` exists

2. **OpenAI API Key Error**
   - Verify your `.env` file exists and contains the correct API key
   - Make sure the API key is valid and has sufficient credits

3. **Port Already in Use**
   - Change the port: `uvicorn src.main:app --reload --host 0.0.0.0 --port 8001`
   - Or kill the process using the port: `lsof -ti:8000 | xargs kill -9`

4. **Virtual Environment Issues**
   - Deactivate and reactivate: `deactivate && source .venv/bin/activate`
   - Recreate virtual environment: `rm -rf .venv && python -m venv .venv`

### Debug Mode
Run the server in debug mode for more detailed error messages:
```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
```

## 10. Development Workflow

### Typical Development Session
```bash
# 1. Activate virtual environment
source .venv/bin/activate

# 2. Install/update dependencies
pip install -r requirements.txt

# 3. Set up environment variables
echo "OPENAI_API_KEY=your-key" > .env

# 4. Start development server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 5. Test API
curl -X POST "http://localhost:8000/chat/test" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "client_id": "test"}'

# 6. Update requirements when adding new packages
pip freeze > requirements.txt
```

## 11. Production Deployment

For production deployment, consider:
- Using a production ASGI server like Gunicorn
- Setting up proper logging
- Using environment variables for configuration
- Implementing rate limiting
- Adding authentication
- Using a proper database for session storage

Example production command:
```bash
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
``` 