"""Entry point to run preprocessing and the Feedback graph."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

from src.graphs.preprocessing import preprocessing_graph
from src.graphs.feedback import feedback_graph


def _load_json(path: Path) -> Dict:
    """Read a JSON file from disk."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_submission_code(submission_dir: Path) -> Dict[str, str]:
    """Load student C source per exercise, keyed by filename stem."""
    if not submission_dir.exists():
        raise FileNotFoundError(f"Submission directory not found: {submission_dir}")
    code_map: Dict[str, str] = {}
    for path in sorted(submission_dir.glob("*.c")):
        code_map[path.stem.replace(" ", "_")] = path.read_text(encoding="utf-8")
    if not code_map:
        raise ValueError(f"No .c files found under {submission_dir}")
    return code_map


def run_preprocessing(preprocess_input: Path) -> Dict:
    """Run the preprocessing graph to build checker prompts."""
    initial_state = _load_json(preprocess_input)
    return preprocessing_graph.invoke(initial_state)


def run_feedback(preprocess_state: Dict, submission_dir: Path) -> Dict:
    """Run the feedback graph using generated prompts and student code."""
    code_by_exercise = _load_submission_code(submission_dir)
    feedback_state = {
        "prompts_by_exercise": preprocess_state.get("prompts_by_exercise", {}),
        "code_by_exercise": code_by_exercise,
    }
    return feedback_graph.invoke(feedback_state)


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Run preprocessing to build prompts then execute the Feedback graph."
    )
    parser.add_argument(
        "--preprocess-input",
        type=Path,
        default=Path("examples/preprocessing_input.json"),
        help="Path to preprocessing input JSON.",
    )
    parser.add_argument(
        "--submission-dir",
        type=Path,
        default=Path("sample_submission/ex08"),
        help="Directory containing student .c files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("feedback_output.json"),
        help="Where to write the aggregated feedback JSON.",
    )
    args = parser.parse_args()

    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    if not os.getenv("LANGCHAIN_PROJECT"):
        os.environ.setdefault("LANGCHAIN_PROJECT", "MagGradeAI-Feedback")

    print("Running preprocessing graph...")
    preprocess_state = run_preprocessing(args.preprocess_input)

    print("Running feedback graph...")
    feedback_state = run_feedback(preprocess_state, args.submission_dir)

    args.output.write_text(
        json.dumps(feedback_state, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Feedback graph complete. Output written to {args.output}")

    print("\nPrompt locations by exercise:")
    for ex_id, prompts in preprocess_state.get("prompts_by_exercise", {}).items():
        print(f"  - {ex_id}: {len(prompts)} prompt(s)")


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set; checkers will not be able to call the model.")
    main()
