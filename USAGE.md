# Agent Usage Guide

## Invoking the Agent with Runtime Configuration

### Critical Requirement: `gcs_root_path`

The agent **requires** `gcs_root_path` to be provided in **every request** via `config.configurable`. This enables multi-tenant workspace isolation.

### Example: Correct Agent Invocation

```python
from langgraph_sdk import get_client

client = get_client(url="http://localhost:8123")

# Create thread
thread = await client.threads.create()

# Invoke agent WITH required config
response = await client.runs.create(
    thread_id=thread["thread_id"],
    assistant_id="agent",
    input={
        "messages": [
            {
                "role": "user",
                "content": "List files in the workspace"
            }
        ]
    },
    config={
        "configurable": {
            "gcs_root_path": "/company-123/workspace-456/"  # ← REQUIRED
        }
    }
)
```

### Path Format

```
/company-{company_id}/workspace-{workspace_id}/
```

- Must start with `/`
- Must end with `/`
- Format: `/company-{id}/workspace-{id}/`
- IDs can contain: alphanumeric, hyphens, underscores
- Examples:
  - ✅ `/company-123/workspace-456/`
  - ✅ `/company-acme-corp/workspace-project-alpha/`
  - ❌ `company-123/workspace-456` (missing slashes)
  - ❌ `/company-123/` (missing workspace)

### What Happens Without `gcs_root_path`

If you don't provide `gcs_root_path` in the config:

```python
# ❌ INCORRECT: Missing gcs_root_path
response = await client.runs.create(
    thread_id=thread_id,
    assistant_id="agent",
    input={"messages": [...]},
    # config missing or without gcs_root_path
)
```

**Result**: Agent will fail with:
```
ValueError: Missing required configuration: 'gcs_root_path'.
Frontend must provide gcs_root_path in config.configurable.
Expected format: /company-{id}/workspace-{id}/
```

## Testing Locally with langgraph-cli

When testing with `langgraph dev`, you can provide config via:

### Option 1: LangGraph Studio

In LangGraph Studio UI:
1. Open "Configuration" panel
2. Add to `configurable`:
   ```json
   {
     "gcs_root_path": "/company-test/workspace-dev/"
   }
   ```

### Option 2: Python SDK

```python
import asyncio
from langgraph_sdk import get_client

async def test_agent():
    client = get_client(url="http://localhost:8123")

    thread = await client.threads.create()

    response = await client.runs.create(
        thread_id=thread["thread_id"],
        assistant_id="agent",
        input={
            "messages": [
                {"role": "user", "content": "List files"}
            ]
        },
        config={
            "configurable": {
                "gcs_root_path": "/company-test/workspace-dev/"
            }
        },
        stream_mode="values"
    )

    async for chunk in response:
        print(chunk)

if __name__ == "__main__":
    asyncio.run(test_agent())
```

### Option 3: HTTP API

```bash
curl -X POST http://localhost:8123/runs/stream \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "messages": [
        {"role": "user", "content": "List files in workspace"}
      ]
    },
    "config": {
      "configurable": {
        "gcs_root_path": "/company-test/workspace-dev/"
      }
    },
    "stream_mode": "values"
  }'
```

## Multi-Tenancy Architecture

### Why Per-Request Configuration?

The agent uses **runtime configuration** instead of environment variables to enable:

1. **True multi-tenancy**: Different requests can access different workspaces
2. **Request-level isolation**: No shared state between requests
3. **Security**: Each request is isolated to its own company/workspace boundary
4. **Flexibility**: Frontend can dynamically route to different workspaces

### How It Works

```
Frontend Request
    ↓ (includes gcs_root_path in config)
Main Agent
    ↓ (ConfigToStateMiddleware: config → state)
SubAgentMiddleware
    ↓ (passes state to sub-agent)
GCS Filesystem Sub-Agent
    ↓ (GCSRuntimeMiddleware: state → context variables)
GCS Tools
    ↓ (read gcs_root_path from context)
Google Cloud Storage
    (operations scoped to /company-{id}/workspace-{id}/)
```

## Frontend Integration Checklist

When integrating with this agent, ensure:

- [ ] Every request includes `config.configurable.gcs_root_path`
- [ ] Path format is `/company-{id}/workspace-{id}/`
- [ ] Company ID and workspace ID are properly validated before sending
- [ ] Error handling for missing/invalid `gcs_root_path`
- [ ] Path is URL-encoded if necessary

## Example Frontend Integration

### React/TypeScript

```typescript
import { Client } from "@langchain/langgraph-sdk";

const client = new Client({
  apiUrl: "http://localhost:8123",
});

async function queryAgent(
  companyId: string,
  workspaceId: string,
  message: string
) {
  const thread = await client.threads.create();

  const stream = client.runs.stream(
    thread.thread_id,
    "agent",
    {
      input: {
        messages: [{ role: "user", content: message }],
      },
      config: {
        configurable: {
          gcs_root_path: `/company-${companyId}/workspace-${workspaceId}/`,
        },
      },
      streamMode: "values",
    }
  );

  for await (const chunk of stream) {
    console.log(chunk);
  }
}

// Usage
queryAgent("123", "456", "List all files");
```

### Python

```python
from langgraph_sdk import get_client

def query_agent(company_id: str, workspace_id: str, message: str):
    client = get_client(url="http://localhost:8123")

    thread = client.threads.create()

    stream = client.runs.stream(
        thread["thread_id"],
        "agent",
        input={"messages": [{"role": "user", "content": message}]},
        config={
            "configurable": {
                "gcs_root_path": f"/company-{company_id}/workspace-{workspace_id}/",
            }
        },
        stream_mode="values",
    )

    for chunk in stream:
        print(chunk)

# Usage
query_agent("123", "456", "List all files")
```

## Troubleshooting

### Error: "Missing required configuration: 'gcs_root_path'"

**Cause**: Request doesn't include `gcs_root_path` in `config.configurable`

**Solution**: Add `config.configurable.gcs_root_path` to your request:

```python
config={
    "configurable": {
        "gcs_root_path": "/company-{id}/workspace-{id}/"
    }
}
```

### Error: "Missing required state key: 'gcs_root_path'"

**Cause**: Sub-agent didn't receive `gcs_root_path` in state (middleware issue)

**Solution**: This should not happen if ConfigToStateMiddleware is properly configured. If you see this:
1. Verify `ConfigToStateMiddleware` is in main agent middleware stack (check `src/agent/main.py`)
2. Verify it's the **first** middleware in the stack
3. Check that you're providing `gcs_root_path` in the request config

### Error: Invalid path format

**Cause**: `gcs_root_path` doesn't match required format

**Solution**: Ensure path matches `/company-{id}/workspace-{id}/`:
- Must start and end with `/`
- Must have exactly two segments after root
- IDs can only contain alphanumeric, hyphens, and underscores

## See Also

- [Architecture Documentation](./architecture.md) - Complete system architecture
- [CLAUDE.md](./CLAUDE.md) - Development guide for Claude Code
- [LangGraph SDK Documentation](https://langchain-ai.github.io/langgraph/cloud/reference/sdk/python_sdk_ref/)
