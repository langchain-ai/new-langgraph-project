# VoicedForm

An intelligent form completion assistant powered by LangGraph and LLM technology. VoicedForm uses a multi-node workflow to guide users through complex form filling processes with AI-driven assistance.

## Overview

VoicedForm is a conversational AI system designed to simplify the process of completing forms. Using a sophisticated workflow orchestrated by LangGraph, the system can:

- Intelligently determine which type of form is needed
- Guide users through form completion step-by-step
- Leverage large language models to provide context-aware assistance
- Validate completed forms before submission
- Support various form types (e.g., accident reports, applications, etc.)

## Architecture

VoicedForm implements a directed acyclic graph (DAG) workflow with the following nodes:

```
Supervisor → Form Selector → Form Completion → Validator
```

### Workflow Components

1. **Supervisor Node**: Analyzes the context and determines the appropriate form type
2. **Form Selector Node**: Uses LLM to identify and describe form fields
3. **Form Completion Node**: Guides interactive form filling with AI assistance
4. **Validator Node**: Verifies the completed form meets requirements

## Prerequisites

- Python 3.9 or higher
- OpenAI API key (for GPT-4 access)
- (Optional) LangSmith API key for tracing and debugging

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd VoicedForm
```

2. Install dependencies:
```bash
pip install -e .
```

3. For development, install with dev dependencies:
```bash
pip install -e . "langgraph-cli[inmem]"
```

## Configuration

1. Create a `.env` file from the example:
```bash
cp .env.example .env
```

2. Add your API keys to the `.env` file:
```bash
# Required
OPENAI_API_KEY=sk-...

# Optional: For LangSmith tracing
LANGSMITH_API_KEY=lsv2...
LANGSMITH_PROJECT=voicedform
```

## Usage

### Running the Prototype

Execute the standalone prototype directly:

```bash
python voicedform_graph.py
```

This will run through a demo workflow showing the complete form processing pipeline.

### Using LangGraph Server

For a more robust deployment with API access:

1. Start the LangGraph development server:
```bash
langgraph dev
```

2. The server will be available at `http://localhost:8123`

3. Access the API endpoints or use LangGraph Studio for visual debugging

### Using LangGraph Studio

LangGraph Studio provides a visual interface for debugging and monitoring your workflows:

1. Start the development server (see above)
2. Open LangGraph Studio
3. Connect to your local server
4. Visualize the workflow execution in real-time

## Development

### Project Structure

```
VoicedForm/
├── src/
│   └── agent/
│       ├── __init__.py
│       └── graph.py          # Main graph definition
├── tests/
│   ├── unit_tests/           # Unit test suite
│   └── integration_tests/    # Integration test suite
├── static/                   # Static assets
├── voicedform_graph.py       # Prototype implementation
├── test_langsmith.py         # LangSmith integration test
├── langgraph.json            # LangGraph configuration
├── pyproject.toml            # Project metadata and dependencies
└── README.md                 # This file
```

### Extending the Graph

To customize the workflow:

1. Edit `src/agent/graph.py` or `voicedform_graph.py`
2. Add new nodes by defining functions that accept state
3. Wire nodes together using `graph.add_edge()`
4. Modify the `GraphState` TypedDict to track additional state

Example:
```python
def custom_node(state: dict) -> dict:
    # Your custom logic here
    return {"new_field": "value"}

graph.add_node("custom", RunnableLambda(custom_node))
graph.add_edge("form_completion", "custom")
```

### Configuration Parameters

Modify the `Configuration` class in `graph.py` to expose runtime parameters:

```python
class Configuration(TypedDict):
    form_type: str
    language: str
    validation_level: str
```

### Running Tests

Execute the test suite:

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit_tests/

# Run integration tests only
pytest tests/integration_tests/
```

### Code Quality

The project uses `ruff` for linting and `mypy` for type checking:

```bash
# Run linter
ruff check .

# Run type checker
mypy src/
```

## Technology Stack

- **LangGraph**: Workflow orchestration framework
- **LangChain**: LLM application framework
- **OpenAI GPT-4**: Language model for intelligent responses
- **LangSmith**: Tracing and observability (optional)
- **Python 3.9+**: Core programming language

## Features

- Multi-step conversational form completion
- Intelligent form type detection
- Context-aware field suggestions
- Form validation and verification
- Hot-reload during development
- Visual debugging with LangGraph Studio
- Comprehensive test coverage

## Tracing and Monitoring

VoicedForm integrates with LangSmith for comprehensive tracing:

- View execution traces for each workflow run
- Debug node-by-node execution
- Monitor performance metrics
- Analyze conversation patterns

Enable tracing by setting `LANGSMITH_API_KEY` in your `.env` file.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Review the [LangGraph documentation](https://langchain-ai.github.io/langgraph/)
- Check [LangChain documentation](https://python.langchain.com/)

## Acknowledgments

Built with [LangGraph](https://github.com/langchain-ai/langgraph) by LangChain.
