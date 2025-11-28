# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **Lucart Agents API** - a LangGraph-based multi-agent system for financial audit workflow automation. The system uses a supervisor pattern with two specialized agents:

- **Auditor Agent** (supervisor): Handles business-level audit requests, interprets requirements, and communicates with users
- **Coder Agent** (assistant): Executes technical database queries against PostgreSQL audit data

The agents work together through a handoff mechanism where the Auditor delegates technical work to the Coder, then interprets results for users.

## Commands

### Setup and Installation
```bash
# Install dependencies (uses UV package manager)
pip install -e . "langgraph-cli[inmem]"

# Setup environment
cp .env.example .env
# Edit .env to add ANTHROPIC_API_KEY and database credentials

# For local development, ensure your .env contains:
# USE_REMOTE_DB=false
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_DB=lucart
# POSTGRES_USER=postgres
# POSTGRES_PASSWORD=postgres
# POSTGRES_SCHEMA=acr

# For Azure deployment, ensure your .env contains:
# USE_REMOTE_DB=true
# DB_URL=postgresql://user:pass@host:port/db?sslmode=require
# POSTGRES_SCHEMA=acr
```

### Development Server
```bash
# Start LangGraph development server with hot reload
langgraph dev
```

### Testing
```bash
# Run all unit tests
make test

# Run specific test file
make test TEST_FILE=tests/unit_tests/test_configuration.py

# Run integration tests
make integration_tests

# Run tests in watch mode
make test_watch
```

### Linting and Formatting
```bash
# Run linters (ruff, mypy)
make lint

# Format code
make format

# Lint only changed files vs main
make lint_diff
make format_diff
```

## Architecture

### Multi-Agent System Design

The application implements a **supervisor-assistant pattern** using LangChain v1 agent framework:

1. **Graph Entry Point** (`src/agent/graph.py`):
   - Creates auditor agent with `create_agent()` from langchain.agents
   - Defines handoff tool (`transfer_to_coder`) that wraps the Coder agent
   - Compiled graph is exposed as `graph` for LangGraph Server
   - Uses LangChain v1 pattern - `create_agent()` returns a compiled graph directly

2. **Agent Definitions**:
   - **Auditor** (`src/agent/graph.py`): Supervisor agent created via `create_agent()` with Claude LLM, transfer tool, and custom prompt
   - **Coder** (`src/agent/agents/coder.py`): Assistant agent created via `create_agent()` with database tools
   - Both agents use the same `create_agent()` factory pattern from LangChain v1

3. **State Management** (`src/agent/agents/states.py`):
   - `AuditorState`: Messages list with LangGraph's `add_messages` reducer, plus optional `remaining_steps`
   - `CoderState`: Same schema - messages and remaining steps
   - States track conversation history and iteration limits

4. **Handoff Mechanism**:
   - Auditor uses `transfer_to_coder` tool (async function decorated with @tool) to delegate technical work
   - Tool directly invokes `coder_assistant.ainvoke()` with business-level request
   - Returns final message text using `.text` property (LangChain v1 pattern)
   - Control automatically returns to Auditor when Coder completes
   - **CRITICAL**: Auditor must always provide final business interpretation to user after Coder responds

### Database Architecture

- **Dual Database Support** (`src/agent/config/settings.py`):
  - Supports both local PostgreSQL (development) and remote Azure PostgreSQL (production)
  - Environment flag `USE_REMOTE_DB` selects database mode
  - Local mode: Uses individual `POSTGRES_*` environment variables
  - Remote mode: Uses complete connection string from `DB_URL`
  - Validation in `DatabaseConfig.__post_init__()` ensures correct configuration on startup
  - `get_connection_params()` method returns appropriate connection parameters for psycopg2

- **Connection Pooling** (`src/agent/utils/database.py`):
  - Singleton `DatabaseManager` class manages psycopg2 connection pool
  - Pool config: 2-10 connections
  - Automatically handles both local and remote connections based on configuration
  - Provides `get_connection()` and `return_connection()` methods

- **Database Tools** (`src/agent/tools/database.py`):
  - Tools are async wrappers around sync database operations (uses ThreadPoolExecutor)
  - `test_database_connection()`: Verifies connectivity and returns DB version
  - `execute_query()`: Executes SELECT queries only (security constraint)
  - Both tools use @tool decorator for LangGraph integration
  - Tools are database-agnostic - work seamlessly with both local and remote databases

- **Schema**: Database uses `acr` schema for audit data tables

### Configuration System

**Environment-based config** (`src/agent/config/settings.py`):
- `DatabaseConfig`: PostgreSQL connection details from env vars
- `ClaudeConfig`: Anthropic API configuration with `get_llm()` factory method
- Uses python-dotenv for .env file loading
- Global instances: `database` and `claude`

**Required Environment Variables**:
- `ANTHROPIC_API_KEY`: Claude API key
- `USE_REMOTE_DB`: Database mode selection (`true` for Azure, `false` for local, defaults to `false`)
- **For Local Database** (when `USE_REMOTE_DB=false`):
  - `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- **For Remote Database** (when `USE_REMOTE_DB=true`):
  - `DB_URL`: Complete PostgreSQL connection string (e.g., `postgresql://user:pass@host:port/db?sslmode=require`)
- `POSTGRES_SCHEMA`: Database schema name (defaults to `acr`, used in both modes)
- Optional: `CLAUDE_MODEL`, `CLAUDE_TEMPERATURE`, `CLAUDE_MAX_TOKENS`
- Optional: `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` for tracing

### Prompt System

**Prompt Loading** (`src/agent/utils/prompts.py`):
- Prompts stored as markdown files in `src/agent/prompts/`
- Resources stored as markdown files in `src/agent/resources/`
- `get_prompt_and_resources()`: Combines base prompt with resources file

**Prompt Architecture**:
- Prompts contain detailed role instructions, workflow patterns, and critical behavioral rules
- Resources contain technical documentation specific to each agent (database schema, query examples)
- Auditor sees audit test documentation; Coder sees SQL implementation guidance
- **Critical Behavioral Rules** in Auditor prompt:
  - **Mandatory Continuation**: Auditor MUST respond after Coder returns results - never let conversation end with Coder's response
  - **Scope Discipline**: Only answer what user explicitly asked - no proactive analysis or additional data gathering
  - **Exception Handling**: When listing exceptions, MUST ask user before deep-dive investigation - never auto-investigate
  - **Professional Formatting**: Specific guidelines for currency/number formatting to ensure clean UI display
  - Absolute prohibition on blank/empty responses

### LangGraph Server Integration

**Configuration** (`langgraph.json`):
- Declares graph location: `agent.graph:graph`
- Uses Wolfi base image for deployment
- Environment variables loaded from `.env`

**Persistence**: LangGraph Server handles thread/checkpoint persistence automatically - no manual implementation needed.

## Migration to LangChain v1 Pattern

The system has been migrated from LangGraph's supervisor framework to LangChain v1's agent pattern:

**Previous Architecture** (LangGraph Supervisor):
- Used `create_supervisor()` for Auditor
- Used `create_react_agent()` for Coder
- Required explicit graph compilation with `.compile()`

**Current Architecture** (LangChain v1):
- Uses `create_agent()` from `langchain.agents` for both agents
- `create_agent()` returns a pre-compiled graph - no manual `.compile()` needed
- Handoff tool (`transfer_to_coder`) wraps Coder agent invocation
- Results extracted using `.text` property on final message (v1 pattern)

**Key Benefits**:
- Simpler, more unified agent creation pattern
- Better alignment with LangChain v1 best practices
- Reduced boilerplate code
- Consistent pattern across both agents

**Implementation Details**:
- Both agents created with identical `create_agent()` signature
- Transfer tool uses async invocation: `await coder_assistant.ainvoke()`
- Message extraction: `result["messages"][-1].text`
- State management remains unchanged (still uses LangGraph states)

## Key Behavioral Patterns

### Agent Interaction Flow

1. User asks audit question → Auditor receives it
2. Auditor analyzes and uses `transfer_to_coder` tool with business-level instructions
3. Coder executes database queries using tools
4. Coder returns structured technical results
5. **CRITICAL**: Auditor MUST immediately respond to user with business interpretation
6. Conversation ends only after Auditor provides final audit conclusion

### Scope Discipline

Both agents follow strict scope rules:
- Only execute/answer what was explicitly requested
- No proactive data gathering or additional analysis beyond the specific question
- No unsolicited recommendations or next steps
- If user asks for summary, provide ONLY summary - no detailed breakdowns unless requested
- If user asks for specific exceptions, provide ONLY those - no additional investigations
- **Exception List Protocol**: When Auditor lists exceptions with mv_ids:
  1. STOP and present the list to user
  2. ASK explicitly: "Would you like me to investigate any of these in detail?"
  3. WAIT for user confirmation before starting deep-dive
  4. Investigate ONE transaction at a time, then ask if user wants another
  5. NEVER auto-investigate - deep-dives are time-intensive and require user approval

### Professional Communication Standards

The Auditor follows strict formatting guidelines for clear, professional audit communication:

**Currency and Number Formatting**:
- Write large amounts clearly: "850 million dollars" (NOT "$850M" or "$850 million")
- **CRITICAL**: Never use dollar signs ($) - they break markdown rendering
- Use "USD" or "dollars" instead: "2.97 million USD" not "$2.97 million"
- Maintain consistent spacing: "from 850 million dollars in 2023 to 12 million dollars in 2025"
- Keep percentages with context: "98% reduction in exceptions"
- Use complete phrases: "300 exceptions in 2024" not "300exceptions"

**Formatting to Avoid (Breaks UI Display)**:
- ❌ Never use dollar signs ($) in responses
- ❌ Never run numbers together: "from300to7"
- ❌ Never concatenate without spaces: "850Min2023"
- ❌ Never omit spaces around prepositions: "from2024to2025"

**Professional Structure**:
- Use complete, well-formed sentences with proper spacing
- Structure responses with clear paragraph breaks between sections
- Keep related financial information together in single phrases

### Error Handling

- Database tools return formatted success/error messages as strings
- Async wrappers handle sync DB operations via ThreadPoolExecutor
- Query validation: Only SELECT statements allowed for security

## Project Structure

```
src/agent/
├── graph.py                 # Main graph definition and supervisor setup
├── config/
│   └── settings.py          # Environment-based configuration
├── agents/
│   ├── states.py            # State schemas for both agents
│   └── coder.py             # Coder ReAct agent definition
├── tools/
│   └── database.py          # Async database tools
├── utils/
│   ├── database.py          # Connection pool manager
│   └── prompts.py           # Prompt loading utilities
├── prompts/
│   ├── auditor_prompt.md    # Auditor system prompt
│   └── coder_prompt.md      # Coder system prompt
└── resources/
    ├── auditor.md           # Auditor-specific resources
    └── coder.md             # Coder-specific resources
```

## Development Notes

- **Python Version**: Requires Python >=3.10
- **Package Manager**: Uses `uv` for dependency management (see uv.lock)
- **LangChain Version**: >=1.0.0 (migrated from LangGraph supervisor to LangChain v1 agent pattern)
- **LangGraph Version**: >=1.0.0 for state management and server integration
- **Agent Framework**: Uses `create_agent()` from langchain.agents for both Auditor and Coder
- **Testing Framework**: pytest with integration and unit test separation
  - Uses `pytest.mark.anyio` for async test support
  - Uses `pytest.mark.langsmith` for LangSmith integration tests
- **Type Checking**: mypy with strict mode enabled
- **Code Quality**: ruff for formatting and linting with pydocstyle (Google convention)
- **Dependency Management**: Uses modern `dependency-groups` in pyproject.toml (PEP 735)

### When Modifying Agents

- Agent prompts are in markdown files - edit `src/agent/prompts/*.md`
  - Auditor prompt contains critical behavioral rules (continuation, scope discipline, exception handling)
  - Changes to behavioral rules require careful testing to ensure agent compliance
- Resources (technical docs) are separate - edit `src/agent/resources/*.md`
  - Resources provide technical context to agents but don't define core behavior
- State schemas must use LangGraph's `add_messages` reducer for message handling
- Both agents use `create_agent()` from langchain.agents (not create_supervisor or create_react_agent)
- Tools must be async and use @tool decorator for LangGraph integration
- Database operations must use connection pool via `db_manager`
- **Critical**: When modifying Auditor behavior, preserve mandatory continuation rules and scope discipline

### When Adding New Tools

1. Implement tool in appropriate module (e.g., `src/agent/tools/`)
2. Use @tool decorator with clear description
3. Make tool async (use ThreadPoolExecutor if wrapping sync code)
4. Add tool to agent definition in graph.py or coder.py
5. Update agent prompt/resources to document tool usage

### When Testing

- Unit tests: `tests/unit_tests/` - test individual components
- Integration tests: `tests/integration_tests/` - test graph execution
  - Use `@pytest.mark.anyio` decorator for async tests
  - Use `@pytest.mark.langsmith` for tests that should be traced in LangSmith
  - Tests invoke graph directly: `await graph.ainvoke(inputs)`
  - Assertions check message structure and multi-agent coordination
- Use `conftest.py` for shared fixtures
- Integration tests require database connection
- Both unit and integration tests use pytest with async support via anyio

## Code Examples

### Creating Agents (LangChain v1 Pattern)

Both agents follow the same creation pattern:

```python
from langchain.agents import create_agent

# Auditor agent with transfer tool
graph = create_agent(
    model=claude.get_llm(),
    tools=[transfer_to_coder],
    system_prompt=get_prompt_and_resources(get_auditor_prompt, "auditor.md"),
    state_schema=AuditorState,
    name="auditor",
)

# Coder agent with database tools
coder_assistant = create_agent(
    model=claude.get_llm(),
    tools=[test_database_connection, execute_query],
    system_prompt=get_prompt_and_resources(get_coder_prompt, "coder.md"),
    state_schema=CoderState,
    name="coder_assistant",
)
```

### Transfer Tool Implementation

```python
from langchain_core.tools import tool

@tool
async def transfer_to_coder(request: str) -> str:
    """Transfer to coder agent for database queries."""
    # Invoke the coder agent
    result = await coder_assistant.ainvoke({
        "messages": [{"role": "user", "content": request}]
    })

    # Extract final message using .text property (v1 pattern)
    return result["messages"][-1].text
```

### Testing Pattern

```python
import pytest

pytestmark = pytest.mark.anyio

@pytest.mark.langsmith
async def test_auditor_agent_basic_response() -> None:
    """Test basic agent functionality."""
    inputs = {
        "messages": [
            {"role": "user", "content": "Hello, can you help me with an audit question?"}
        ]
    }
    res = await graph.ainvoke(inputs)

    assert res is not None
    assert "messages" in res
    assert len(res["messages"]) > 1
```

## LangGraph Server Deployment

Graph is automatically deployed via LangGraph Server when running `langgraph dev`. The server:
- Exposes HTTP API for graph invocation
- Handles checkpointing and thread management
- Provides streaming responses
- Integrates with LangSmith for tracing (if configured)
