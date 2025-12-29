# MagGradeAI - Automated C Code Grader

Welcome to MagGradeAI, a flexible and extensible framework for automatically grading C programming assignments.

This project uses a multi-agent system, powered by LangGraph, to create a pipeline that analyzes, compiles, tests, and scores student submissions based on a customizable rubric.

## Architecture

The grading process is broken down into a series of agents, each with a specific responsibility. These agents operate sequentially, passing a shared state object that accumulates findings.

1.  **Orchestrator**: The entry point of the grading process. It reads the assignment rubric and determines which checks need to be run.

2.  **Static Analyzer**: Performs static analysis on the student's code to check for style, conventions, and potential issues without executing the code.

3.  **Compiler Runner**: Compiles the student's C code using `gcc`. It reports any compilation errors or warnings.

4.  **Unit Tester**: Executes the compiled program against a set of predefined test cases from the rubric, comparing the actual output to the expected output.

5.  **Rubric Scorer**: The final agent in the pipeline. It aggregates the findings from all previous agents and maps them to the rubric to calculate a final score and generate feedback in Hebrew.

## Getting Started

This guide will help you set up and run the project on your local machine or on an AWS EC2 instance.

### Local Setup

#### Prerequisites

- Python 3.10+
- Pip for package management
- `gcc` for compiling C code

#### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    ```

2.  **Set up the environment:**
    - Create a virtual environment:
      ```bash
      python -m venv .venv
      source .venv/bin/activate
      ```
    - Install the required dependencies:
      ```bash
      make install
      ```

3.  **Configure API Keys:**
    - Copy the example environment file:
      ```bash
      cp .env.example .env
      ```
    - Add your API keys (e.g., for a large language model) to the `.env` file:
      ```
      # .env
      API_KEY="YOUR_API_KEY_HERE"
      ```

### Cloud Setup (EC2 Ubuntu)

#### 1. Set Up an EC2 Instance

1.  **Launch an EC2 Instance**:
    *   Choose an **Ubuntu** Amazon Machine Image (AMI).
    *   Select an instance type (e.g., `t2.micro` or `t3.small`).
    *   Configure a security group to allow SSH access (port 22).
    *   Launch the instance and save your private key file (`.pem`).

2.  **Connect to your instance**:
    ```bash
    ssh -i /path/to/your-key.pem ubuntu@<your-ec2-instance-public-ip>
    ```

#### 2. Install Prerequisites

Once connected to your EC2 instance, install Python, pip, git, and gcc.
```bash
sudo apt-get update
sudo apt-get install -y python3.10 python3.10-venv python3-pip git gcc
```

#### 3. Set Up the Project

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd MagGradeAI
    ```

2.  **Create a virtual environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    make install
    ```

4.  **Configure API Keys**:
    ```bash
    cp .env.example .env
    nano .env
    ```
    Add your API key to the `.env` file.

### Usage

To grade a submission, you will need to:

1.  Place the student's code in a directory.
2.  Define a rubric YAML file in the `rubrics/` directory for the assignment.
3.  Update the main application entry point to start the grading process with the path to the submission and the rubric.

## Development Environment

For the Magshimim development team, the EC2 instance is configured as follows:

-   **Server Address**: `ubuntu@35.164.240.64`
-   **Virtual Environment Activation**: `source /home/ubuntu/MagGradeAI/MagGradeAIEnv/bin/activate`

## Customization

### Rubrics

Rubrics are defined in YAML files within the `rubrics/` directory. See `rubrics/example_assignment.yml` for a template. You can define compilation flags, static analysis rules, and unit test cases.

### Agents

Each agent is a Python class in the `src/agents/` directory. You can modify the logic of each agent to use different tools or perform custom checks.

### Tools

Python functions that agents can use (e.g., for running shell commands) are located in the `src/tools/` directory. You can add new tools to extend the capabilities of your agents.

## Micro-Agent Feedback Architecture (Graph V2)

We have introduced a new, modular architecture for generating feedback, located in `src/graphs/feedback_v2/`. This system uses specialized "Micro-Agents" to analyze specific aspects of student code.

### Core Components

1.  **Strict Protocols (`schemas.py`)**: All agents communicate using defined JSON schemas (`AgentInput`, `AgentOutput`), ensuring consistency.
2.  **Orchestrator (`orchestrator.py`)**: Manages the flow of data between agents and handles the aggregation of results.
3.  **Validators (`validators/`)**: Ensure that agent outputs match the expected format before passing them on.
4.  **Aggregator (`aggregator.py`)**: Compiles specific findings from all agents into a single, unified feedback report.

### Available Agents

-   **Flow & Structure Agent**: Analyzes execution flow, logical structure, and requirement coverage.
-   **Function Division Agent**: Checks for modularity, function breakdown, and single responsibility.
-   **Programming Errors Agent**: Detects syntax errors, bugs, and potential runtime issues.
-   **Conventions & Documentation Agent**: Enforces PEP8, naming conventions, and docstring standards.
-   **Debug Tasks Agent**: Verifies fixes for specific debugging/refactoring exercises.

### Configuration for Developers

#### Adding a New Agent
1.  Create a new class in `src/graphs/feedback_v2/agents/` inheriting from `BaseAgent`.
2.  Implement `name`, `role_description`, and `get_system_prompt`.
3.  Register the new agent in `src/graphs/feedback_v2/orchestrator.py` list.

#### Verification
To verify the graph structure and agent flow without making real LLM calls:

```bash
python3 tests/verify_feedback_v2.py
```

This script mocks the LLM responses and ensures the graph topology and data validation are correct.

### Running on a Dataset

We provide a utility script to run the feedback graph on a large dataset of student submissions.

#### 1. Prepare Data (JSONL)
Create a `.jsonl` file where each line is a valid JSON object containing:
- `code`: The C code submission (string).
- `exercise_description`: The problem statement (string).
- `previous_feedback`: (Optional) List of previous feedback strings.

**Example `input.jsonl`:**
```json
{"code": "void main() { ... }", "exercise_description": "Print hello world"}
{"code": "int main() { return 0; }", "exercise_description": "Return 0"}
```

#### 2. Run the Script
```bash
python3 scripts/run_feedback_on_dataset.py input.jsonl output.jsonl
```

#### 3. Analyze Output
The `output.jsonl` file will contain a copy of the input records with an added `feedback_result` field:

```json
{
  "code": "...",
  "exercise_description": "...",
  "feedback_result": {
    "status": "PASS",
    "summary": "Passed: 5, Failed: 0, Warnings: 0",
    "details": [
      {"agent_name": "Flow Agent", "status": "PASS", "comments": []},
      ...
    ]
  }
}
```