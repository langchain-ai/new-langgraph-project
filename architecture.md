# Architecture Documentation

## Overview

This project implements a **multi-layer LangGraph agent system** with specialized sub-agents for different operational domains. The architecture enables:

- **Task delegation**: Main agent delegates specialized tasks to sub-agents
- **Model optimization**: Different models per agent type (Sonnet for reasoning, Haiku for file ops)
- **Runtime configuration**: Per-request workspace isolation without shared state
- **Middleware composition**: Layered middleware for config propagation, validation, and tool injection

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend/Client                          │
│                                                                 │
│  POST /api/agent                                                │
│  {                                                              │
│    "messages": [...],                                           │
│    "config": {                                                  │
│      "configurable": {                                          │
│        "gcs_root_path": "/company-123/workspace-456/"          │
│      }                                                          │
│    }                                                            │
│  }                                                              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Main Agent                               │
│                    (Claude Sonnet 4.5)                          │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Middleware Stack (executed in order):                    │ │
│  │                                                           │ │
│  │ 1. ConfigToStateMiddleware                               │ │
│  │    └─> config.configurable → state                       │ │
│  │                                                           │ │
│  │ 2. TodoListMiddleware                                    │ │
│  │    └─> Task tracking for user visibility                │ │
│  │                                                           │ │
│  │ 3. SubAgentMiddleware                                    │ │
│  │    └─> Provides 'task' tool for delegating to sub-agents│ │
│  │                                                           │ │
│  │ 4. SummarizationMiddleware                               │ │
│  │    └─> Condenses conversation history                   │ │
│  │                                                           │ │
│  │ 5. AnthropicPromptCachingMiddleware                      │ │
│  │    └─> Enables prompt caching for cost optimization     │ │
│  │                                                           │ │
│  │ 6. PatchToolCallsMiddleware                              │ │
│  │    └─> Handles tool call formatting                     │ │
│  │                                                           │ │
│  │ 7. HumanInTheLoopMiddleware                              │ │
│  │    └─> Requires approval for write operations           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Tools: [task]                                                  │
│  - No direct tools, all operations delegated via 'task' tool   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ task("gcs-filesystem", ...)
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   GCS Filesystem Sub-Agent                      │
│                     (Claude Haiku 4.5)                          │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Middleware Stack:                                         │ │
│  │                                                           │ │
│  │ 1. GCSRuntimeMiddleware                                  │ │
│  │    └─> state → context variables (set_gcs_root_path)    │ │
│  │                                                           │ │
│  │ 2. TodoListMiddleware                                    │ │
│  │ 3. SummarizationMiddleware                               │ │
│  │ 4. AnthropicPromptCachingMiddleware                      │ │
│  │ 5. PatchToolCallsMiddleware                              │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Tools: [ls, read_file, write_file, edit_file]                 │
│  - All tools read gcs_root_path from context variables         │
└─────────────────────────────────────────────────────────────────┘
```

## Runtime Configuration Flow

### The Two-Middleware Pattern

The system uses **two middleware classes** to propagate `gcs_root_path` from request config to GCS tools:

```
config.configurable.gcs_root_path
         │
         │ ConfigToStateMiddleware (Main Agent)
         ▼
state['gcs_root_path']
         │
         │ SubAgentMiddleware.ainvoke(state)
         ▼
sub_agent_state['gcs_root_path']
         │
         │ GCSRuntimeMiddleware (Sub-Agent)
         ▼
context_var: _gcs_root_path
         │
         │ GCS Tools: get_gcs_root_path()
         ▼
"/company-123/workspace-456/"
```

### Why Two Middleware?

#### ConfigToStateMiddleware (Main Agent)
**Purpose**: Copy `config.configurable.gcs_root_path` → `state['gcs_root_path']`

**Why needed**: deepagents `SubAgentMiddleware` doesn't propagate `RunnableConfig` when calling `subagent.ainvoke(state)`. Without this middleware, the sub-agent would never receive the runtime configuration.

**Code location**: `src/agent/middleware/config_to_state.py`

```python
class ConfigToStateMiddleware(AgentMiddleware):
    def before_agent(self, state, runtime):
        config = get_config()
        gcs_root_path = config.get("configurable", {}).get("gcs_root_path")
        if not gcs_root_path:
            raise ValueError("Missing gcs_root_path in config")
        return {"gcs_root_path": gcs_root_path}

    async def abefore_agent(self, state, runtime):
        return self.before_agent(state, runtime)
```

#### GCSRuntimeMiddleware (Sub-Agent)
**Purpose**: Read `state['gcs_root_path']` → call `set_gcs_root_path()` (context variable)

**Why needed**: GCS tools use context variables for thread-safe per-request isolation. This middleware validates the path format and sets it in the context.

**Code location**: `src/agent/sub_agents/gcs_filesystem/middleware.py`

```python
class GCSRuntimeMiddleware(AgentMiddleware):
    def before_agent(self, state, runtime):
        root_path = state.get("gcs_root_path")
        if not root_path:
            raise ValueError("Missing gcs_root_path in state")

        # Normalize path
        if not root_path.startswith("/"):
            root_path = f"/{root_path}"
        if not root_path.endswith("/"):
            root_path = f"{root_path}/"

        # Set in context for tools
        set_gcs_root_path(root_path)
        return None

    async def abefore_agent(self, state, runtime):
        return self.before_agent(state, runtime)
```

### Critical: Async/Sync Middleware Implementation

**IMPORTANT**: Both sync (`before_agent`) and async (`abefore_agent`) methods must be implemented.

**Why**: Sub-agents are invoked asynchronously via `ainvoke()`. LangGraph calls `abefore_agent()` in async contexts. If only `before_agent()` is implemented, the middleware logic **never executes**.

**Pattern**: Delegate async to sync for fast, in-memory operations:

```python
async def abefore_agent(self, state, runtime):
    """Async version delegates to sync for fast operations."""
    return self.before_agent(state, runtime)
```

This is acceptable because middleware operations are:
- In-memory (no I/O)
- Fast (microseconds)
- Synchronous by nature

## Model Configuration

Models are centrally configured in `src/agent/config/models_config.py`:

```python
# Model identifiers
CLAUDE_HAIKU_4_5 = "claude-haiku-4-5-20251001"
CLAUDE_SONNET_4_5 = "claude-sonnet-4-5-20250929"

# Sub-agent model mappings
SUBAGENT_MODELS = {
    "gcs-filesystem": CLAUDE_HAIKU_4_5,  # Fast, cheap for file ops
}
```

**Main agent**: Sonnet 4.5 (configured in `src/agent/main.py`)
**Sub-agents**: Haiku 4.5 by default (or custom per sub-agent)

**To change a sub-agent's model**:
1. Edit `SUBAGENT_MODELS` in `models_config.py`
2. Map sub-agent name to desired model identifier

## Sub-Agent Registry

All sub-agents must be registered in `src/agent/sub_agents/registry.py`:

```python
def get_subagents():
    """Factory function that creates sub-agents on demand."""
    return [
        GCS_FILESYSTEM_SUBAGENT(),  # Lazy initialization
        # Add new sub-agents here
    ]
```

**Lazy initialization**: Sub-agents are created via factory functions to allow environment variables to be set before instantiation.

## GCS Filesystem Tools

### Tool Architecture

**Shared utilities** (`src/agent/tools/shared/gcs/`):
- `client.py`: GCS client initialization with authentication
- `validation.py`: Path validation, context variable management
- `file_operations.py`: Core file operations (read, write, edit, list)
- `formatting.py`: Output formatting for agent responses
- `models.py`: Pydantic models for structured data

**GCS Filesystem Tools** (`src/agent/tools/gcs_filesystem/`):
- `ls.py`: List files and directories
- `read_file.py`: Read file contents
- `write_file.py`: Create new files
- `edit_file.py`: Apply edits to existing files

### Context Variable Pattern

Tools use context variables for thread-safe runtime configuration:

```python
# In validation.py
_gcs_root_path: ContextVar[str] = ContextVar("gcs_root_path")

def set_gcs_root_path(root_path: str) -> None:
    """Set path in context (called by middleware)."""
    _gcs_root_path.set(root_path)

def get_gcs_root_path() -> str:
    """Get path from context (called by tools)."""
    return _gcs_root_path.get()
```

**Benefits**:
- Thread-safe: Each request has isolated context
- No shared state: Enables true multi-tenancy
- Per-request configuration: Different workspaces per request

## State Propagation

### Excluded State Keys

deepagents `SubAgentMiddleware` excludes certain keys when creating sub-agent state:

```python
_EXCLUDED_STATE_KEYS = ("messages", "todos")

# From deepagents/middleware/subagents.py:332
subagent_state = {k: v for k, v in runtime.state.items()
                  if k not in _EXCLUDED_STATE_KEYS}
```

**Why messages excluded**: Sub-agent gets fresh message list with task description
**Why todos excluded**: Each agent maintains independent todo lists

**Custom state keys** (like `gcs_root_path`) **are propagated** ✅

## Adding New Sub-Agents

### Step-by-Step Guide

1. **Create sub-agent directory**:
   ```
   src/agent/sub_agents/your_agent/
   ├── __init__.py
   ├── agent.py        # Sub-agent configuration
   ├── prompts.py      # System prompts
   └── middleware.py   # (Optional) Custom middleware
   ```

2. **Implement sub-agent configuration** (`agent.py`):
   ```python
   def create_your_subagent():
       """Create sub-agent configuration."""
       return {
           "name": "your-agent",
           "description": "What this agent does",
           "system_prompt": YOUR_AGENT_SYSTEM_PROMPT,
           "tools": [tool1, tool2],
           "middleware": [],  # Optional custom middleware
       }

   def YOUR_AGENT_SUBAGENT():
       """Lazy getter for sub-agent."""
       return create_your_subagent()
   ```

3. **Register in registry** (`src/agent/sub_agents/registry.py`):
   ```python
   from .your_agent import YOUR_AGENT_SUBAGENT

   def get_subagents():
       return [
           GCS_FILESYSTEM_SUBAGENT(),
           YOUR_AGENT_SUBAGENT(),  # Add here
       ]
   ```

4. **(Optional) Add model mapping** (`src/agent/config/models_config.py`):
   ```python
   SUBAGENT_MODELS = {
       "gcs-filesystem": CLAUDE_HAIKU_4_5,
       "your-agent": CLAUDE_SONNET_4_5,  # Add here
   }
   ```

5. **(Optional) Add human approval for tools** (`src/agent/main.py`):
   ```python
   WRITE_OPERATIONS_APPROVAL = {
       "write_file": True,
       "edit_file": True,
       "your_risky_tool": True,  # Add here
   }
   ```

## Environment Variables

Required environment variables (configured in `.env`):

```bash
# GCS Authentication (JSON service account key)
GOOGLE_CLOUD_CREDENTIALS_JSON='{"type": "service_account", ...}'

# GCS Bucket Name
GCS_BUCKET_NAME='your-bucket-name'

# Anthropic API Key
ANTHROPIC_API_KEY='sk-ant-...'
```

**Note**: `gcs_root_path` is **NOT** an environment variable. It's provided per-request via `config.configurable` for multi-tenant workspace isolation.

## Running the Agent

```bash
# Set environment variables
export GOOGLE_CLOUD_CREDENTIALS_JSON='...'
export GCS_BUCKET_NAME='your-bucket-name'
export ANTHROPIC_API_KEY='sk-ant-...'

# Run with langgraph-cli
langgraph dev
```

## Testing

```bash
# Run all tests
make test

# Run specific test file
make test TEST_FILE=tests/unit_tests/test_specific.py

# Run integration tests
make integration_tests

# Watch mode
make test_watch
```

## Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Lint specific areas
make lint_package  # Only src/
make lint_tests    # Only tests/
```

## Key Design Principles

### 1. Multi-Tenancy via Runtime Configuration
- No shared state between requests
- Workspace isolation via per-request `gcs_root_path`
- Context variables for thread-safe configuration

### 2. Model Optimization
- Sonnet 4.5 for complex reasoning (main agent)
- Haiku 4.5 for fast operations (file sub-agent)
- Configurable per sub-agent

### 3. Lazy Initialization
- Sub-agents created on demand
- Environment variables set before creation
- Factory pattern for flexibility

### 4. Middleware Composition
- Layered middleware for separation of concerns
- Config → State → Context propagation
- Async/sync compatibility required

### 5. Workaround Architecture
- Two-middleware pattern compensates for deepagents limitation
- When deepagents fixes config propagation, can simplify to one middleware
- Documented for future refactoring

## Future Improvements

### When deepagents Fixes Config Propagation

Currently: `subagent.ainvoke(state)` doesn't pass config

Future: `subagent.ainvoke(state, config=runtime.config)`

**Impact**:
- ✅ Remove `ConfigToStateMiddleware` entirely
- ✅ `GCSRuntimeMiddleware` reads directly from `config.configurable`
- ✅ Simpler architecture with one middleware instead of two

### Tracking Issue
Watch for updates: https://github.com/anthropics/deepagents/issues

## References

- **Main Agent**: `src/agent/main.py`
- **Sub-Agent Registry**: `src/agent/sub_agents/registry.py`
- **Model Configuration**: `src/agent/config/models_config.py`
- **GCS Middleware**: `src/agent/sub_agents/gcs_filesystem/middleware.py`
- **Config Middleware**: `src/agent/middleware/config_to_state.py`
- **GCS Tools**: `src/agent/tools/gcs_filesystem/`
- **Shared GCS Utilities**: `src/agent/tools/shared/gcs/`
