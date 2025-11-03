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

> **📖 For comprehensive architecture documentation**, see [architecture.md](./architecture.md) for detailed diagrams, middleware flow patterns, state propagation mechanics, and the complete two-middleware architecture explanation.

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

**Critical for multi-tenancy**: Workspace isolation is achieved through per-request configuration.

**Flow**:
1. Frontend sends: `config.configurable = {company_slug: 'acme-corp', workspace_slug: 'cliente-1'}`
2. **Main Agent**: `ConfigToStateMiddleware` builds GCS path:
   - Input: `company_slug`, `workspace_slug`
   - Output: `gcs_root_path = 'athena-enterprise/{company_slug}/{workspace_slug}/'`
   - Saves to `state['gcs_root_path']`
3. **Sub-Agent**: Receives `gcs_root_path` in state (via `CompiledSubAgent` with `state_schema=MainAgentState`)
4. **GCSRuntimeMiddleware**: Validates path format
5. **Tools**: Read `gcs_root_path` from `runtime.state` (NOT from ContextVar)

**CRITICAL Tool Pattern**:
```python
def my_tool(arg1, arg2, runtime: ToolRuntime = None):
    root_path = get_root_path_from_runtime(runtime)  # From runtime.state
    # Use root_path for operations
```

**Why runtime.state instead of ContextVar**:
- ContextVar is thread-local and doesn't propagate across async tasks
- Tools execute in different async context than middleware
- `runtime.state` is guaranteed available in tool execution

**Why this matters**:
- Each request isolated by company/workspace
- Multi-tenant SaaS architecture
- No shared state between requests
- Path mapping separates frontend logic from backend storage

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

## State Management

### Main Agent State Schema

**Location**: `src/agent/state.py`

The main agent uses `MainAgentState` which extends `AgentState` to include custom fields:

```python
class MainAgentState(AgentState):
    gcs_root_path: Optional[str]
```

**Why this matters**:
- `create_agent()` uses default schema (only `messages`) if not specified
- Custom state fields require explicit `state_schema` parameter
- Both main agent AND sub-agents must use same state schema to share fields

### State Propagation Flow

**Main Agent → Sub-Agent**:
1. Main agent has `state_schema=MainAgentState` in `create_agent()`
2. `ConfigToStateMiddleware` copies `gcs_root_path` from config to state
3. `SubAgentMiddleware` passes ALL state fields (except `messages`, `todos`) to sub-agent
4. Sub-agent MUST have `state_schema=MainAgentState` to receive custom fields
5. Sub-agent middleware reads custom fields from state

**CRITICAL**: If sub-agent uses default schema, it will ONLY receive `messages` even if main agent has custom fields in state.

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

### CompiledSubAgent vs SubAgent

**CRITICAL**: When sharing custom state fields beyond `messages`, sub-agents MUST use the `CompiledSubAgent` format.

**SubAgent format** (dict config):
- ❌ Cannot specify `state_schema`
- ❌ Only receives `messages` in state
- ✅ Simple for basic sub-agents with no custom state

**CompiledSubAgent format** (pre-compiled runnable):
- ✅ Can specify `state_schema` via `create_agent()`
- ✅ Receives all state fields (e.g., `gcs_root_path`)
- ✅ Required for multi-tenant or shared state scenarios
- ⚠️ Model MUST be explicitly provided (cannot be None)

### Implementation Steps

1. **Create directory**: `src/agent/sub_agents/<name>/`

2. **Implement `agent.py`** with `create_<name>_subagent()`:
   ```python
   from langchain.agents import create_agent
   from src.agent.config.models_config import get_subagent_model
   from src.agent.state import MainAgentState

   def create_my_subagent(model=None):
       # Get model from config if not provided
       if model is None:
           model = get_subagent_model("my-subagent")
       if model is None:
           raise ValueError("Model required for CompiledSubAgent")

       # Create compiled graph with state_schema
       compiled_subagent = create_agent(
           model=model,
           tools=[...],
           system_prompt="...",
           middleware=[...],
           state_schema=MainAgentState,  # Share custom state
       )

       # Return CompiledSubAgent format
       return {
           "name": "my-subagent",
           "description": "...",
           "runnable": compiled_subagent,
       }
   ```

3. **Add system prompt** in `prompts.py`

4. **Add middleware** if needed (e.g., for runtime config extraction)

5. **Register** in `src/agent/sub_agents/registry.py`

6. **Add model mapping** in `src/agent/config/models_config.py`:
   ```python
   SUBAGENT_MODELS = {
       "my-subagent": CLAUDE_HAIKU_4_5,
   }
   ```

7. **Update state schema** in `src/agent/state.py` if adding new fields:
   ```python
   class MainAgentState(AgentState):
       my_custom_field: Optional[str]
   ```

8. **Update `WRITE_OPERATIONS_APPROVAL`** in `main.py` if tools require approval

## Human-in-the-Loop

Write operations (`write_file`, `edit_file`) require user approval via `HumanInTheLoopMiddleware`. This is configured in `main.py`:

```python
WRITE_OPERATIONS_APPROVAL = {
    "write_file": True,
    "edit_file": True,
}
```

Add new tools to this dictionary if they require approval.

## Key Learnings

### Runtime Parameters: Always Use `runtime.state`

**Rule**: For runtime parameters (per-request config), ALWAYS pass via state and read from `runtime.state` in tools.

**Why ContextVar doesn't work**:
- ContextVar is thread-local
- Tools execute in different async task than middleware
- Context is not propagated across task boundaries

**Pattern**:
```python
# Tool implementation
def my_tool(arg1, arg2, runtime: ToolRuntime = None):
    param = runtime.state["my_param"]  # ✅ Works
    # NOT: param = _context_var.get()  # ❌ Fails across async tasks
```

**Helper pattern for DRY**:
```python
def get_param_from_runtime(runtime: ToolRuntime) -> str:
    if not runtime or "my_param" not in runtime.state:
        raise RuntimeError("Param not found in runtime state")
    return runtime.state["my_param"]
```

### Path Mapping for Multi-Tenancy

**Pattern**: Frontend passes logical identifiers, backend maps to storage paths.

**Benefits**:
- Frontend doesn't know storage structure
- Easy to change storage organization
- Clear separation of concerns

**Example** (GCS):
- Frontend: `company_slug='acme'`, `workspace_slug='client1'`
- Backend builds: `athena-enterprise/acme/client1/`

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
