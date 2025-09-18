#!/bin/bash

set -e

# Load environment variables from .env if it exists
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

MODEL_NAME=${MODEL_NAME:-qwen3:1.7b}

# Start Ollama server in the background if not already running
if ! lsof -i:11434 >/dev/null 2>&1; then
  echo "Starting Ollama server..."
  ollama serve &
  OLLAMA_PID=$!
  sleep 2
else
  echo "Ollama server already running on port 11434."
fi

# Pull and run the model if not already present
if ! ollama list | grep -q "$MODEL_NAME"; then
  echo "Pulling Ollama model: $MODEL_NAME"
  ollama pull "$MODEL_NAME"
fi

echo "Running Ollama model: $MODEL_NAME"
ollama run "$MODEL_NAME" &
OLLAMA_MODEL_PID=$!
sleep 2

# Run LangGraph dev server
uv run langgraph dev

# Optionally, kill background processes on exit
trap 'kill $OLLAMA_PID $OLLAMA_MODEL_PID 2>/dev/null' EXIT
