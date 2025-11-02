# GCS Filesystem Tools

This module provides tools for interacting with Google Cloud Storage as a filesystem.

## Tools Available

- **ls**: List files and directories
- **read_file**: Read file contents
- **write_file**: Create new files
- **edit_file**: Modify existing files

## Root Path Configuration

All GCS filesystem tools require a valid root path to ensure proper workspace isolation.
The root path determines the base directory for all file operations.

### Runtime Configuration

The root path is provided by the frontend in the runtime configuration with each request:

```javascript
// Frontend passes configuration
const config = {
  configurable: {
    gcs_root_path: "/company-123/workspace-456/"  // Required for each request
  }
}
```

The tools automatically read this configuration at runtime through context variables:

```python
# Tools are created once at startup
tools = get_gcs_tools(bucket_name="my-bucket")

# Root path is read from runtime config when tools are executed
# No need to pass it during tool creation
```

### How It Works

1. **Frontend sends request** with `gcs_root_path` in `config.configurable`
2. **GCSRuntimeMiddleware** extracts and validates the root path
3. **Context variables** make the path available to tools
4. **Tools read** the root path from context when executed
5. **Workspace isolation** is enforced for all operations

This approach ensures:
- Root path is specific to each request/user
- Multi-tenancy support (different workspaces per request)
- Security through runtime validation
- No environment variable dependencies

## Authentication

Tools also require GCS authentication via the `@require_gcs_auth` decorator:
```bash
export GOOGLE_CLOUD_CREDENTIALS_JSON='{"type": "service_account", ...}'
```

## Usage in Sub-Agents

When used as a sub-agent, the GCS filesystem tools are automatically configured:

```python
from src.agent.sub_agents.gcs_filesystem import create_gcs_filesystem_subagent

subagent = create_gcs_filesystem_subagent(
    bucket_name="my-bucket",
    root_path="/company-123/workspace-456/"
)
```

The sub-agent handles:
- Tool initialization
- Root path validation
- Error handling
- Context isolation