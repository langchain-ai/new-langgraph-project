# AE-Agent: LangGraph Multi-Tenant Agent with GCS Integration

A production-ready LangGraph agent system with specialized sub-agents for Google Cloud Storage operations, designed for multi-tenant SaaS applications.

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud Platform account with GCS access
- Anthropic API key

### Installation

```bash
# Install dependencies
pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials
```

### Running the Agent

```bash
# Start the agent server
langgraph dev
```

The agent will be available at `http://localhost:8123`.

## 📋 Key Features

- **Multi-Tenant Architecture**: Per-request workspace isolation via runtime configuration
- **Specialized Sub-Agents**: Delegated task execution with optimized models
- **GCS Integration**: Full filesystem operations (ls, read, write, edit) on Google Cloud Storage
- **Human-in-the-Loop**: Write operations require user approval
- **Model Optimization**: Sonnet 4.5 for reasoning, Haiku 4.5 for file operations

## 📖 Documentation

- **[USAGE.md](./USAGE.md)** - How to invoke the agent with required configuration
- **[architecture.md](./architecture.md)** - Complete system architecture and design patterns
- **[CLAUDE.md](./CLAUDE.md)** - Development guide for working with this codebase

## 🔑 Required Configuration

**CRITICAL**: Every request MUST include `gcs_root_path` in the configuration:

```python
config={
    "configurable": {
        "gcs_root_path": "/company-123/workspace-456/"
    }
}
```

See [USAGE.md](./USAGE.md) for complete examples.

## 🏗️ Architecture Overview

```
Frontend Request (with gcs_root_path)
    ↓
Main Agent (Sonnet 4.5)
    ├── ConfigToStateMiddleware (config → state)
    ├── SubAgentMiddleware (task delegation)
    └── Other middleware...
    ↓
Sub-Agent: GCS Filesystem (Haiku 4.5)
    ├── GCSRuntimeMiddleware (state → context)
    └── Tools: ls, read_file, write_file, edit_file
    ↓
Google Cloud Storage
```

See [architecture.md](./architecture.md) for detailed diagrams and explanations.

## 🛠️ Development

### Testing

```bash
# Run all tests
make test

# Run specific test
make test TEST_FILE=tests/unit_tests/test_specific.py

# Run integration tests
make integration_tests

# Watch mode
make test_watch
```

### Linting & Formatting

```bash
# Format code
make format

# Lint code
make lint

# Lint specific areas
make lint_package  # Only src/
make lint_tests    # Only tests/
```

### Debugging Middleware Flow

```bash
# Run middleware flow tests
python test_middleware_flow.py
```

## 📦 Project Structure

```
src/agent/
├── config/
│   └── models_config.py          # Centralized model configuration
├── main.py                        # Main agent entry point
├── middleware/
│   └── config_to_state.py         # Config → State propagation
├── sub_agents/
│   ├── registry.py                # Sub-agent registration
│   └── gcs_filesystem/
│       ├── agent.py               # Sub-agent configuration
│       ├── middleware.py          # Runtime path extraction
│       └── prompts.py             # System prompts
└── tools/
    ├── shared/gcs/                # Reusable GCS utilities
    └── gcs_filesystem/            # GCS filesystem tools
```

## 🔧 Environment Variables

Create a `.env` file with:

```bash
# GCS Authentication (JSON service account key)
GOOGLE_CLOUD_CREDENTIALS_JSON='{"type": "service_account", ...}'

# GCS Bucket Name
GCS_BUCKET_NAME='your-bucket-name'

# Anthropic API Key
ANTHROPIC_API_KEY='sk-ant-...'
```

**Note**: `gcs_root_path` is NOT an environment variable. It's provided per-request via configuration for multi-tenant isolation.

## 🎯 Example Usage

### Python SDK

```python
from langgraph_sdk import get_client

client = get_client(url="http://localhost:8123")
thread = await client.threads.create()

response = await client.runs.create(
    thread_id=thread["thread_id"],
    assistant_id="agent",
    input={
        "messages": [
            {"role": "user", "content": "List files in workspace"}
        ]
    },
    config={
        "configurable": {
            "gcs_root_path": "/company-123/workspace-456/"  # Required!
        }
    }
)
```

### HTTP API

```bash
curl -X POST http://localhost:8123/runs/stream \
  -H "Content-Type: "application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "messages": [{"role": "user", "content": "List files"}]
    },
    "config": {
      "configurable": {
        "gcs_root_path": "/company-test/workspace-dev/"
      }
    }
  }'
```

## 🚨 Troubleshooting

### "Missing required configuration: 'gcs_root_path'"

You forgot to include `gcs_root_path` in the request config. See [USAGE.md](./USAGE.md#critical-requirement-gcs_root_path).

### "Missing required state key: 'gcs_root_path'"

This indicates a middleware configuration issue. Verify:
1. `ConfigToStateMiddleware` is in main agent middleware stack
2. It's the first middleware in the stack
3. You're providing `gcs_root_path` in the request config

Run `python test_middleware_flow.py` to debug.

## 📚 Dependencies

Core:
- `deepagents>=0.1.4` - Sub-agent middleware
- `langgraph>=1.0.0` - LangGraph framework
- `google-cloud-storage>=2.18.2` - GCS client
- `langchain-anthropic` - Claude integration

Dev:
- `ruff` - Linter/formatter
- `mypy` - Type checker
- `pytest` - Testing framework

## 🤝 Contributing

When adding new sub-agents:

1. Create directory: `src/agent/sub_agents/<name>/`
2. Implement `agent.py` with configuration
3. Register in `src/agent/sub_agents/registry.py`
4. Add model mapping in `src/agent/config/models_config.py`
5. Run tests: `make test`

See [CLAUDE.md](./CLAUDE.md#adding-new-sub-agents) for detailed guide.

## 📄 License

MIT

## 🙏 Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph)
- [Anthropic Claude](https://www.anthropic.com)
- [deepagents](https://github.com/anthropics/deepagents)
