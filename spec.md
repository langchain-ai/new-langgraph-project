# VoicedForm Project Specification

## 1. Project Overview

### 1.1 Purpose
VoicedForm is a LangGraph-based application designed to facilitate voice-driven form completion using AI agents. The project demonstrates a multi-node workflow system that guides users through structured form completion processes with AI assistance.

### 1.2 Technology Stack
- **Framework**: LangGraph (>=0.2.6)
- **AI/LLM**: OpenAI GPT-4 via LangChain
- **Language**: Python 3.9+
- **Development Tools**: LangGraph Studio, LangSmith
- **Testing**: pytest with async support (anyio)
- **Linting/Formatting**: ruff, mypy
- **Container**: Docker with Wolfi Linux distro

### 1.3 Project Structure
```
VoicedForm/
├── src/agent/                  # Main agent implementation
│   ├── __init__.py            # Module exports
│   └── graph.py               # Template graph definition
├── tests/
│   ├── unit_tests/            # Unit test suite
│   └── integration_tests/     # Integration test suite
├── .github/workflows/         # CI/CD pipelines
├── voicedform_graph.py        # Custom VoicedForm workflow
├── test_langsmith.py          # LangSmith integration test
├── langgraph.json             # LangGraph server configuration
├── pyproject.toml             # Project dependencies
└── Makefile                   # Development commands
```

---

## 2. Architecture

### 2.1 System Design
The application follows a **state-based graph architecture** using LangGraph:

```
Input → Supervisor → Form Selector → Form Completion → Validator → Output
```

### 2.2 Core Architectural Patterns
1. **State Graph Pattern**: Nodes represent discrete processing steps with shared state
2. **LLM Integration**: OpenAI models provide intelligent decision-making and natural language processing
3. **Configuration-Driven**: Runtime behavior controlled via configurable parameters
4. **Async-First**: Asynchronous execution for scalability

### 2.3 Execution Model
- **Synchronous Execution**: Nodes execute sequentially based on graph edges
- **State Persistence**: State flows through nodes, accumulating data
- **Terminal Condition**: Graph terminates at END node after validation

---

## 3. Core Components

### 3.1 Template Graph (`src/agent/graph.py`)

**Purpose**: Minimal template demonstrating LangGraph structure.

#### State Schema
```python
@dataclass
class State:
    changeme: str = "example"  # Placeholder input field
```

#### Configuration Schema
```python
class Configuration(TypedDict):
    my_configurable_param: str  # Runtime configuration parameter
```

#### Nodes
- **`call_model`**: Single processing node that returns configured output

#### Graph Definition
- **Entry Point**: `__start__` → `call_model`
- **Compilation**: Named "New Graph"

### 3.2 VoicedForm Graph (`voicedform_graph.py`)

**Purpose**: Production implementation for form completion workflows.

#### State Schema
```python
class GraphState(TypedDict, total=False):
    input: Optional[str]          # User input
    form_type: Optional[str]      # Type of form to complete
    first_field: Optional[str]    # First field description from LLM
    form_complete: Optional[str]  # Completed form content
    valid: Optional[bool]         # Validation status
```

#### Nodes

##### 1. **Supervisor Node**
- **Role**: Entry point, route determination
- **Function**: Decides which form type to process
- **Output**: Sets `form_type` (currently stubbed to "accident_report")

##### 2. **Form Selector Node**
- **Role**: Form template identification
- **Function**: Uses LLM to describe form structure
- **Input**: `form_type`
- **Output**: `first_field` (description of initial form field)
- **LLM Prompt**: "You are helping complete a form of type: {form_type}. What's the first field?"

##### 3. **Form Completion Node**
- **Role**: Interactive form filling
- **Function**: Simulates form completion with LLM assistance
- **Input**: `first_field`
- **Output**: `form_complete`
- **LLM Prompt**: "Let's pretend to fill out this form together."

##### 4. **Validator Node**
- **Role**: Output verification
- **Function**: Validates form completion
- **Logic**: Checks for presence of `form_complete` in state
- **Output**: `valid` (boolean)

#### Graph Flow
```
START → supervisor → form_selector → form_completion → validator → END
```

---

## 4. State Management

### 4.1 State Flow
State is a **mutable dictionary** that flows through the graph:

1. **Input State**: Initialized with optional user input
2. **Node Processing**: Each node reads and updates state
3. **State Accumulation**: New keys added without overwriting existing
4. **Terminal State**: Final state contains all accumulated data

### 4.2 State Keys
| Key | Type | Source Node | Purpose |
|-----|------|------------|---------|
| `input` | str | External | User's initial input |
| `form_type` | str | supervisor | Form category selection |
| `first_field` | str | form_selector | LLM-generated field description |
| `form_complete` | str | form_completion | Completed form content |
| `valid` | bool | validator | Validation status |

---

## 5. LLM Integration

### 5.1 Model Configuration
```python
llm = ChatOpenAI(model="gpt-4", temperature=0)
```

- **Model**: GPT-4 (OpenAI)
- **Temperature**: 0 (deterministic output)
- **API Key**: Loaded from environment variable `OPENAI_API_KEY`

### 5.2 Usage Patterns
1. **Invoke**: Synchronous LLM call with string prompt
2. **Response**: Returns structured message with `content` attribute
3. **Context Injection**: Form type and state data embedded in prompts

---

## 6. Configuration & Environment

### 6.1 Environment Variables
Required in `.env` file:

```bash
OPENAI_API_KEY=sk-...          # OpenAI API key
LANGSMITH_API_KEY=lsv2...      # LangSmith tracing key (optional)
LANGSMITH_PROJECT=new-agent    # LangSmith project name
```

### 6.2 LangGraph Configuration (`langgraph.json`)
```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/agent/graph.py:graph"
  },
  "env": ".env",
  "image_distro": "wolfi"
}
```

- **Dependencies**: Local package installation
- **Graphs**: Maps "agent" to template graph
- **Environment**: Loads `.env` file
- **Image**: Uses Wolfi Linux for containers

---

## 7. Dependencies

### 7.1 Core Dependencies
```toml
langgraph>=0.2.6       # Graph framework
python-dotenv>=1.0.1   # Environment management
langchain-openai       # OpenAI LLM integration
langchain-core         # Core LangChain utilities
```

### 7.2 Development Dependencies
```toml
pytest>=8.3.5              # Testing framework
anyio>=4.7.0               # Async utilities
langgraph-cli[inmem]>=0.2.8  # LangGraph CLI
mypy>=1.13.0               # Type checking
ruff>=0.8.2                # Linting and formatting
```

---

## 8. Development Workflow

### 8.1 Setup
```bash
# Install dependencies
pip install -e . "langgraph-cli[inmem]"

# Configure environment
cp .env.example .env
# Edit .env with API keys

# Start development server
langgraph dev
```

### 8.2 Available Commands (Makefile)

| Command | Description |
|---------|-------------|
| `make test` | Run unit tests |
| `make integration_tests` | Run integration tests |
| `make lint` | Run linters (ruff, mypy) |
| `make format` | Format code with ruff |
| `make test_watch` | Run tests in watch mode |

### 8.3 Code Quality Standards
- **Linting**: ruff with pycodestyle, pyflakes, isort
- **Type Checking**: mypy with strict mode
- **Documentation**: Google-style docstrings
- **Formatting**: Automatic with ruff

---

## 9. Testing Strategy

### 9.1 Unit Tests (`tests/unit_tests/`)

**File**: `test_configuration.py`
- **Purpose**: Validate graph instantiation
- **Test**: Confirms graph is a Pregel instance
- **Coverage**: Graph structure validation

### 9.2 Integration Tests (`tests/integration_tests/`)

**File**: `test_graph.py`
- **Purpose**: End-to-end graph execution
- **Test**: `test_agent_simple_passthrough`
  - **Input**: `{"changeme": "some_val"}`
  - **Assertion**: Non-null response
- **Markers**: `@pytest.mark.anyio`, `@pytest.mark.langsmith`

### 9.3 Manual Tests
- **`test_langsmith.py`**: Validates OpenAI connection
- **`voicedform_graph.py`**: Executable workflow test with debug output

---

## 10. Deployment

### 10.1 LangGraph Server
The application deploys as a LangGraph Server instance:

```bash
langgraph dev  # Development mode with hot reload
```

**Server Features**:
- REST API endpoints for graph invocation
- WebSocket support for streaming
- Built-in authentication (if configured)
- LangSmith tracing integration

### 10.2 Container Deployment
- **Base Image**: Wolfi Linux (minimal, security-focused)
- **Build System**: setuptools with wheel
- **Package Structure**: Dual namespace (`agent`, `langgraph.templates.agent`)

### 10.3 CI/CD Pipelines
Located in `.github/workflows/`:

1. **`unit-tests.yml`**: Runs unit test suite on push/PR
2. **`integration-tests.yml`**: Runs integration tests with LangSmith

---

## 11. Observability & Monitoring

### 11.1 LangSmith Integration
- **Tracing**: Automatic trace capture for all LLM calls
- **Project Isolation**: Traces grouped by `LANGSMITH_PROJECT`
- **Debug Output**: Console logging for local development

### 11.2 Logging Strategy
Console logging with emoji prefixes for visual clarity:
- 🧭 Supervisor decisions
- 📄 Form selection
- ✍️ Form completion
- ✅ Validation results

---

## 12. Extensibility

### 12.1 Adding New Nodes
1. Define node function with signature: `(state: dict) -> dict`
2. Wrap with `RunnableLambda` if needed
3. Add to graph: `graph.add_node("name", function)`
4. Define edges: `graph.add_edge("source", "target")`

### 12.2 Custom Configurations
Modify `Configuration` class in `graph.py`:
```python
class Configuration(TypedDict):
    system_prompt: str
    model_name: str
    temperature: float
```

### 12.3 Multi-Graph Support
Update `langgraph.json` to expose multiple graphs:
```json
{
  "graphs": {
    "agent": "./src/agent/graph.py:graph",
    "voicedform": "./voicedform_graph.py:dag"
  }
}
```

---

## 13. Current Limitations & Future Work

### 13.1 Limitations
1. **Supervisor Stubbed**: Always returns "accident_report"
2. **No Persistence**: State not saved between sessions
3. **Single Form Type**: Only accident reports supported
4. **Mock Completion**: Form filling is simulated
5. **Basic Validation**: Only checks for key presence

### 13.2 Proposed Enhancements
1. **Dynamic Form Selection**: LLM-based form type detection from user input
2. **Multi-Step Forms**: Support for complex, multi-page forms
3. **Database Integration**: Store completed forms
4. **Voice Input**: Integrate speech-to-text for true voice-driven UX
5. **Validation Rules**: Schema-based validation with error recovery
6. **User Authentication**: Session management and user identification
7. **Form Templates**: JSON-based form definitions
8. **Export Formats**: PDF, JSON, CSV output options

---

## 14. API Reference

### 14.1 Graph Invocation (Template)
```python
from agent import graph

# Synchronous
result = graph.invoke({"changeme": "input"})

# Asynchronous
result = await graph.ainvoke({"changeme": "input"})
```

### 14.2 Graph Invocation (VoicedForm)
```python
from voicedform_graph import dag

result = dag.invoke({})  # Empty initial state
# Returns: {
#   "form_type": "accident_report",
#   "first_field": "...",
#   "form_complete": "...",
#   "valid": True
# }
```

### 14.3 Configuration Override
```python
result = graph.invoke(
    {"changeme": "input"},
    config={"configurable": {"my_configurable_param": "value"}}
)
```

---

## 15. Security Considerations

### 15.1 API Key Management
- **Storage**: Environment variables only (never commit)
- **Rotation**: Regular key rotation recommended
- **Scope**: Minimum required permissions

### 15.2 Input Validation
- **Current**: No input sanitization
- **Risk**: Potential prompt injection
- **Recommendation**: Validate and sanitize user inputs

### 15.3 Output Handling
- **PII Concern**: Forms may contain sensitive data
- **Recommendation**: Implement encryption at rest
- **Compliance**: Consider GDPR/HIPAA requirements

---

## 16. Performance Characteristics

### 16.1 Latency Profile
- **LLM Calls**: 2 per execution (form_selector, form_completion)
- **Expected Latency**: 2-5 seconds per form completion
- **Bottleneck**: OpenAI API response time

### 16.2 Scalability
- **Concurrency**: Supports async execution
- **Rate Limits**: Bound by OpenAI tier limits
- **Optimization**: Consider caching for repeated queries

---

## 17. Version History

### v0.0.1 (Current)
- Initial prototype with basic form completion workflow
- Template graph implementation
- OpenAI GPT-4 integration
- LangGraph Studio support
- CI/CD pipeline setup

---

## 18. Contributing Guidelines

### 18.1 Code Standards
- Follow PEP 8 via ruff formatting
- Type hints required (enforced by mypy --strict)
- Docstrings required for public functions (Google style)
- Test coverage for new features

### 18.2 Commit Workflow
1. Create feature branch
2. Implement changes with tests
3. Run `make lint` and `make test`
4. Submit PR with description
5. Ensure CI passes

---

## 19. License
MIT License - See LICENSE file for details

---

## 20. Contact & Resources

### Documentation
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- [LangGraph Server](https://langchain-ai.github.io/langgraph/concepts/langgraph_server/)
- [LangSmith](https://smith.langchain.com/)

### Repository
- **Original Template**: https://github.com/langchain-ai/new-langgraph-project
- **Author**: William Fu-Hinthorn (hinthornw@users.noreply.github.com)

---

*Last Updated: 2025-11-13*
*Document Version: 1.0*
