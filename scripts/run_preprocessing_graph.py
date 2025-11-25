#!/usr/bin/env python
"""CLI helper for running the preprocessing graph end-to-end."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.core.preprocessing_state import PreprocessingState, ReferenceSolutionInput
from src.graphs.preprocessing import preprocessing_graph


def _normalize_solution_id(raw: str) -> str:
    """Normalize filenames like 'Exc4 - cyberKioskSolution' to rubric ids."""
    cleaned = raw.replace(" - ", "_")
    cleaned = cleaned.replace(" ", "_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned


def _parse_metadata(pairs: List[str]) -> Dict[str, str]:
    metadata: Dict[str, str] = {}
    for pair in pairs:
        if "=" not in pair:
            raise argparse.ArgumentTypeError(
                f"Metadata '{pair}' must be in key=value format."
            )
        key, value = pair.split("=", maxsplit=1)
        metadata[key] = value
    return metadata


def _gather_reference_solutions(reference_dir: Path) -> List[ReferenceSolutionInput]:
    if not reference_dir.exists():
        raise FileNotFoundError(f"Reference directory not found: {reference_dir}")

    references: List[ReferenceSolutionInput] = []
    for path in sorted(reference_dir.iterdir()):
        if not path.is_file():
            continue
        solution_id = _normalize_solution_id(path.stem)
        references.append(
            ReferenceSolutionInput(
                solution_id=solution_id,
                path=str(path),
            )
        )
    if not references:
        raise ValueError(f"No files found under {reference_dir}")
    return references


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build checker prompts for every rubric subtopic."
    )
    parser.add_argument(
        "--rubric",
        type=Path,
        default=Path("rubrics/rubric.yaml"),
        help="Path to the rubric YAML file.",
    )
    parser.add_argument(
        "--reference-dir",
        type=Path,
        default=Path("sample_submission/ex08"),
        help="Directory containing official reference C solutions.",
    )
    parser.add_argument(
        "--metadata",
        type=str,
        nargs="*",
        default=[],
        help="Optional metadata entries in key=value form.",
    )
    parser.add_argument(
        "--debug-solutions",
        type=str,
        nargs="*",
        default=[],
        help=(
            "Optional solution_ids to mark as debug. These are flagged in the output "
            "state and skipped when building checker prompts."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to save the resulting JSON state.",
    )

    args = parser.parse_args()
    references = _gather_reference_solutions(args.reference_dir)
    metadata = _parse_metadata(args.metadata)

    initial_state: PreprocessingState = {
        "rubric_path": str(args.rubric),
        "reference_solutions": references,
        "metadata": metadata,
        "debug_exercises": args.debug_solutions,
    }

    result_state = preprocessing_graph.invoke(initial_state)
    # Strip internal fields we don't need in the saved output.
    for key in ["prompts_by_subtopic", "normalized_reference_solutions"]:
        result_state.pop(key, None)

    output_text = json.dumps(result_state, indent=2, ensure_ascii=False)

    if args.output:
        args.output.write_text(output_text, encoding="utf-8")
        print(f"Wrote preprocessing output to {args.output}")
    else:
        print(output_text)


if __name__ == "__main__":
    main()
