"""Feedback LangGraph: run checkers, validators, and aggregators."""

from __future__ import annotations

from typing import Dict, List, TypedDict

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph


class CheckerResult(TypedDict):
    exercise_id: str
    subtopic_id: str
    response: str
    prompt_used: str
    code_used: str


class FeedbackState(TypedDict, total=False):
    prompts_by_exercise: Dict[str, Dict[str, Dict]]
    code_by_exercise: Dict[str, str]
    checker_results: List[CheckerResult]
    validated_results: List[CheckerResult]
    aggregated_feedback: Dict[str, str]


def run_checkers(state: FeedbackState) -> FeedbackState:
    """Invoke checker prompts per exercise/subtopic against the student code."""
    prompts = state.get("prompts_by_exercise") or {}
    code_map = state.get("code_by_exercise") or {}
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    results: List[CheckerResult] = []
    for exercise_id, subtopics in prompts.items():
        code = code_map.get(exercise_id, "")
        for subtopic_id, prompt in subtopics.items():
            system = prompt.get("checker_prompt", "")
            messages = [SystemMessage(content=system), HumanMessage(content=code)]
            response = model.invoke(messages).content
            results.append(
                CheckerResult(
                    exercise_id=exercise_id,
                    subtopic_id=subtopic_id,
                    response=response,
                    prompt_used=system,
                    code_used=code,
                )
            )

    state["checker_results"] = results
    return state


def validate_results(state: FeedbackState) -> FeedbackState:
    """Lightweight validator that retries once if PASS/FAIL is missing."""
    validated: List[CheckerResult] = []
    for result in state.get("checker_results", []):
        # Minimal validator: ensure response is non-empty and mentions PASS/FAIL or equivalent.
        text = (result.get("response") or "").strip().lower()
        if not text or ("pass" not in text and "fail" not in text):
            # Re-run the checker once if validation fails.
            prompt = result["prompt_used"]
            code = result["code_used"]
            model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            messages = [SystemMessage(content=prompt), HumanMessage(content=code)]
            rerun = model.invoke(messages).content
            result["response"] = rerun
        validated.append(result)

    state["validated_results"] = validated
    return state


def aggregate_feedback(state: FeedbackState) -> FeedbackState:
    """Aggregate validated checker outputs into per-exercise feedback (Hebrew labels)."""
    aggregated: Dict[str, List[str]] = {}
    for result in state.get("validated_results", []):
        ex = result["exercise_id"]
        aggregated.setdefault(ex, []).append(
            f"- [{result['subtopic_id']}] {result['response']}"
        )

    state["aggregated_feedback"] = {
        ex: f"משוב עבור תרגיל {ex}:\n" + "\n".join(lines)
        for ex, lines in aggregated.items()
    }
    return state


def build_feedback_graph() -> StateGraph:
    workflow = StateGraph(FeedbackState)
    workflow.add_node("run_checkers", run_checkers)
    workflow.add_node("validate_results", validate_results)
    workflow.add_node("aggregate_feedback", aggregate_feedback)

    workflow.add_edge(START, "run_checkers")
    workflow.add_edge("run_checkers", "validate_results")
    workflow.add_edge("validate_results", "aggregate_feedback")
    workflow.add_edge("aggregate_feedback", END)

    return workflow


feedback_graph = build_feedback_graph().compile()

__all__ = ["feedback_graph", "build_feedback_graph"]
