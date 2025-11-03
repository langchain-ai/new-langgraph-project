# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **LangGraph-based agent** that integrates with Google Cloud Storage (GCS) through a sub-agent architecture. The main agent delegates GCS filesystem operations to a specialized sub-agent, enabling multi-tenancy and workspace isolation.

## Development Commands

### Testing
```bash
# Run all tests
make test

# Run specific test file
make test TEST_FILE=tests/unit_tests/test_specific.py

# Run integration tests
make integration_tests

# Run tests in watch mode
make test_watch
```

### Linting and Formatting
```bash
# Format code (uses ruff)
make format

# Run linters (ruff + mypy with strict mode)
make lint

# Lint specific areas
make lint_package  # Only src/
make lint_tests    # Only tests/
```

### Running the Agent

The agent is configured via `langgraph.json` and runs as a LangGraph application:

```bash
# Set environment variables first
export GOOGLE_CLOUD_CREDENTIALS_JSON='{"type": "service_account", ...}'
export GCS_BUCKET_NAME='your-bucket-name'

# Run with langgraph-cli
langgraph dev
```

## Architecture

### Multi-Layer Agent System

**Main Agent** (`src/agent/main.py`):
- Uses `SubAgentMiddleware` from `deepagents` package
- Model: Sonnet 4.5 (configurable in `src/agent/config/models_config.py`)
- No direct tools - all operations delegated to sub-agents
- Includes middleware stack: ConfigToState (workaround), TodoList, SubAgent, Summarization, PromptCaching, HumanInTheLoop

**Sub-Agent: GCS Filesystem** (`src/agent/sub_agents/gcs_filesystem/`):
- Specialized agent for Google Cloud Storage operations
- Model: Haiku 4.5 (faster, cheaper for file operations)
- Tools: `ls`, `read_file`, `write_file`, `edit_file`
- Middleware: `GCSRuntimeMiddleware` for path extraction and validation

### Model Configuration (Centralized)

**Location**: `src/agent/config/models_config.py`

This file centralizes all Claude model identifiers:
- `CLAUDE_HAIKU_4_5 = "claude-haiku-4-5-20251001"`
- `CLAUDE_SONNET_4_5 = "claude-sonnet-4-5-20250929"`
- `SUBAGENT_MODELS` dictionary maps sub-agent names to their models

**To change which model a sub-agent uses**, edit `SUBAGENT_MODELS` in `models_config.py`:

```python
SUBAGENT_MODELS = {
    "gcs-filesystem": CLAUDE_HAIKU_4_5,  # Change to CLAUDE_SONNET_4_5 if needed
}
```

### Sub-Agent Registry

**Location**: `src/agent/sub_agents/registry.py`

All sub-agents must be registered in `get_subagents()`. To add a new sub-agent:

1. Create sub-agent in `src/agent/sub_agents/<name>/`
2. Import in `registry.py`
3. Add to `get_subagents()` return list
4. (Optional) Add model mapping in `models_config.py`

### GCS Runtime Configuration Flow

**Critical for multi-tenancy**: The GCS root path is provided **per-request** by the frontend, not via environment variables.

**Flow**:
1. Frontend sends request with `config.configurable.gcs_root_path = "/company-123/workspace-456/"`
2. **Main Agent**: `ConfigToStateMiddleware.before_agent()` copies `gcs_root_path` from config to state
3. **Sub-Agent**: `GCSRuntimeMiddleware.before_agent()` reads path from state
4. Middleware validates and normalizes path format
5. Middleware sets path in context using `set_gcs_root_path()`
6. GCS tools read path from context using `get_gcs_root_path()`

**WORKAROUND NOTE**: Steps 2-3 implement a temporary workaround for deepagents `SubAgentMiddleware`
not propagating `RunnableConfig` to sub-agents when calling `subagent.ainvoke()`.
The `ConfigToStateMiddleware` copies config to state so sub-agents can access runtime configuration.
When deepagents fixes config propagation, this middleware can be removed and step 3 changed to read directly from config.

**Why this matters**:
- Each request can specify a different workspace
- Supports multi-tenant SaaS architecture
- No shared state between requests
- Security through runtime validation

### GCS Tools Architecture

**Shared utilities** (`src/agent/tools/shared/gcs/`):
- `client.py`: GCS client initialization with authentication
- `validation.py`: Path validation and context management
- `file_operations.py`: Core file operations (read, write, edit, list)
- `formatting.py`: Output formatting for agent responses
- `models.py`: Pydantic models for structured data

**GCS Filesystem Tools** (`src/agent/tools/gcs_filesystem/`):
- `ls.py`: List files and directories
- `read_file.py`: Read file contents
- `write_file.py`: Create new files
- `edit_file.py`: Apply edits to existing files
- `config.py`: Tool configuration and descriptions

**Design principle**: Tools are **created once at startup** with bucket name only. The root path is injected at runtime via context variables, enabling per-request isolation.

## Environment Configuration

Required environment variables (set in `.env`):

```bash
# GCS Authentication (JSON service account key)
GOOGLE_CLOUD_CREDENTIALS_JSON='{"type": "service_account", ...}'

# GCS Bucket Name (workspace isolation handled via runtime config)
GCS_BUCKET_NAME='your-bucket-name'

# Anthropic API Key (for Claude models)
ANTHROPIC_API_KEY='sk-ant-...'
```

## Code Structure

```
src/agent/
├── config/
│   └── models_config.py          # Centralized model configuration
├── main.py                        # Main agent entry point
├── sub_agents/
│   ├── registry.py                # Sub-agent registration
│   └── gcs_filesystem/
│       ├── agent.py               # Sub-agent configuration
│       ├── middleware.py          # Runtime path extraction
│       └── prompts.py             # System prompts
└── tools/
    ├── shared/gcs/                # Reusable GCS utilities
    │   ├── client.py
    │   ├── validation.py
    │   ├── file_operations.py
    │   └── formatting.py
    └── gcs_filesystem/            # GCS filesystem tools
        ├── ls.py
        ├── read_file.py
        ├── write_file.py
        └── edit_file.py
```

## Key Design Patterns

### 1. Sub-Agent Delegation
The main agent has no direct tools. All operations are delegated to specialized sub-agents via `SubAgentMiddleware`. This enables:
- Model optimization per task type (Haiku for file ops, Sonnet for reasoning)
- Isolated middleware stacks per sub-agent
- Independent tool configurations

### 2. Runtime Configuration Injection
Instead of environment variables for workspace paths, configuration is passed per-request through `config.configurable`. This enables:
- Multi-tenancy without environment variable changes
- Request-level isolation
- Dynamic workspace switching

### 3. Lazy Sub-Agent Initialization
Sub-agents use lazy initialization via factory functions (`GCS_FILESYSTEM_SUBAGENT()`). This allows:
- Environment variables to be set before sub-agent creation
- Testing with different configurations
- Delayed validation of required environment variables

## Adding New Sub-Agents

1. Create directory: `src/agent/sub_agents/<name>/`
2. Implement `agent.py` with `create_<name>_subagent()` function
3. Add system prompt in `prompts.py`
4. Add middleware if needed (e.g., for runtime config)
5. Register in `src/agent/sub_agents/registry.py`
6. Add model mapping in `src/agent/config/models_config.py`
7. Update `WRITE_OPERATIONS_APPROVAL` in `main.py` if tools require human approval

## Human-in-the-Loop

Write operations (`write_file`, `edit_file`) require user approval via `HumanInTheLoopMiddleware`. This is configured in `main.py`:

```python
WRITE_OPERATIONS_APPROVAL = {
    "write_file": True,
    "edit_file": True,
}
```

Add new tools to this dictionary if they require approval.

## Dependencies

Core dependencies:
- `deepagents>=0.1.4` - Sub-agent middleware and utilities
- `langgraph>=1.0.0` - LangGraph framework
- `google-cloud-storage>=2.18.2` - GCS client library
- `langchain-anthropic` - Claude model integration

Dev dependencies:
- `ruff` - Fast Python linter/formatter
- `mypy` - Static type checker (strict mode)
- `pytest` - Testing framework
