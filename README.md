# Lucart Agents API

[![CI](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/unit-tests.yml)
[![Integration Tests](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/integration-tests.yml/badge.svg)](https://github.com/langchain-ai/new-langgraph-project/actions/workflows/integration-tests.yml)

A LangGraph-based multi-agent system for financial audit workflow automation. The system uses a supervisor pattern with two specialized agents:

- **Auditor Agent** (supervisor): Handles business-level audit requests, interprets requirements, and communicates with users
- **Coder Agent** (assistant): Executes technical database queries against PostgreSQL audit data

The agents work together through a handoff mechanism where the Auditor delegates technical work to the Coder, then interprets results for users.

<div align="center">
  <img src="./static/studio_ui.png" alt="Graph view in LangGraph studio UI" width="75%" />
</div>

## Features

- **Multi-Agent Coordination**: Supervisor-assistant pattern using LangChain v1 agents
- **Dual Database Support**: Seamlessly switch between local PostgreSQL (development) and Azure PostgreSQL (production)
- **LangSmith Integration**: Full tracing and observability support
- **Type-Safe Configuration**: Environment-based configuration with validation
- **Async Database Tools**: Connection pooling with async wrappers for PostgreSQL operations

## Getting Started

1. Install dependencies, along with the [LangGraph CLI](https://langchain-ai.github.io/langgraph/concepts/langgraph_cli/), which will be used to run the server.

```bash
cd path/to/your/app
pip install -e . "langgraph-cli[inmem]"
```

2. Create a `.env` file and configure your environment.

```bash
cp .env.example .env
```

Configure required environment variables in `.env`:

**For Local Development:**
```bash
# Anthropic API
ANTHROPIC_API_KEY=your-api-key-here

# Database Configuration
USE_REMOTE_DB=false
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=lucart
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_SCHEMA=acr

# Optional: LangSmith Tracing
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2...
LANGSMITH_PROJECT=lucart-agents
```

**For Azure Deployment:**
```bash
# Anthropic API
ANTHROPIC_API_KEY=your-api-key-here

# Database Configuration
USE_REMOTE_DB=true
DB_URL=postgresql://user:pass@pg-lucart-dev.postgres.database.azure.com:5432/lucart_db_dev?sslmode=require
POSTGRES_SCHEMA=acr

# Optional: LangSmith Tracing
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2...
LANGSMITH_PROJECT=lucart-agents
```

3. Start the LangGraph Server.

```shell
langgraph dev
```

For more information on getting started with LangGraph Server, [see here](https://langchain-ai.github.io/langgraph/tutorials/langgraph-platform/local-server/).

## Database Configuration

The system supports dual database modes:

### Local PostgreSQL (Development)
Set `USE_REMOTE_DB=false` and provide individual connection parameters:
- `POSTGRES_HOST`: Database host (default: localhost)
- `POSTGRES_PORT`: Database port (default: 5432)
- `POSTGRES_DB`: Database name
- `POSTGRES_USER`: Database user
- `POSTGRES_PASSWORD`: Database password
- `POSTGRES_SCHEMA`: Schema name (default: acr)

### Azure PostgreSQL (Production)
Set `USE_REMOTE_DB=true` and provide a complete connection string:
- `DB_URL`: Full PostgreSQL connection string with SSL (e.g., `postgresql://user:pass@host:port/db?sslmode=require`)
- `POSTGRES_SCHEMA`: Schema name (default: acr)

The application validates your configuration on startup and provides clear error messages if required variables are missing.

## How to customize

1. **Modify Agent Prompts**: Edit prompts in `src/agent/prompts/` to customize agent behavior and instructions.

2. **Add Database Tools**: Implement new tools in `src/agent/tools/database.py` using the `@tool` decorator for LangGraph integration.

3. **Extend Agent Resources**: Update technical documentation in `src/agent/resources/` to provide agents with domain-specific knowledge.

4. **Adjust Agent State**: Modify state schemas in `src/agent/agents/states.py` to track additional information across agent interactions.

## Development

While iterating on your graph in LangGraph Studio, you can edit past state and rerun your app from previous states to debug specific nodes. Local changes will be automatically applied via hot reload.

Follow-up requests extend the same thread. You can create an entirely new thread, clearing previous history, using the `+` button in the top right.

### Testing

Run tests using the provided Makefile commands:

```bash
# Run all unit tests
make test

# Run integration tests (requires database connection)
make integration_tests

# Run specific test file
make test TEST_FILE=tests/unit_tests/test_configuration.py

# Format and lint code
make format
make lint
```

**Note**: Integration tests require a configured database connection. Ensure your `.env` file has valid database credentials before running integration tests.

## Documentation

For detailed implementation information, see:
- [CLAUDE.md](./CLAUDE.md) - Comprehensive project documentation for AI assistants
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/) - Official LangGraph guides and examples

## LangSmith Integration

LangGraph Studio integrates with [LangSmith](https://smith.langchain.com/) for tracing, debugging, and collaboration. Enable tracing by setting:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-api-key
LANGSMITH_PROJECT=lucart-agents
```

**Important**: Use `LANGSMITH_*` environment variables (not the older `LANGCHAIN_*` naming) for proper tracing integration.

