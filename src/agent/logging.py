"""Logging and monitoring utilities for 5STARS agent.

Provides event logging and integration with LangSmith.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Optional

# Configure LangSmith tracing if API key is available
if os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ.setdefault("LANGCHAIN_PROJECT", "5stars")


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Setup logging for 5STARS agent.

    Args:
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("5stars")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(level)
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


class EventLogger:
    """Structured event logging for 5STARS operations."""

    def __init__(self):
        """Initialize event logger."""
        self.logger = logging.getLogger("5stars.events")

    def log_case_created(
        self,
        case_id: int,
        rating: int,
        customer: str,
        review_preview: str = "",
    ) -> None:
        """Log case creation event.

        Args:
            case_id: Case identifier
            rating: Star rating
            customer: Customer name or ID
            review_preview: First 50 chars of review
        """
        self.logger.info(
            f"CASE_CREATED | case_id={case_id} | rating={rating}⭐ | "
            f"customer={customer} | preview={review_preview[:50]}..."
        )

    def log_stage_transition(
        self,
        case_id: int,
        from_stage: str,
        to_stage: str,
        reason: Optional[str] = None,
    ) -> None:
        """Log stage transition event.

        Args:
            case_id: Case identifier
            from_stage: Previous stage
            to_stage: New stage
            reason: Optional reason for transition
        """
        msg = f"STAGE_TRANSITION | case_id={case_id} | {from_stage} → {to_stage}"
        if reason:
            msg += f" | reason={reason}"
        self.logger.info(msg)

    def log_message_sent(
        self,
        case_id: int,
        message_id: str,
        message_length: int,
        channel: str = "wb",
    ) -> None:
        """Log message sent event.

        Args:
            case_id: Case identifier
            message_id: Message identifier
            message_length: Length of message
            channel: Communication channel (wb, telegram)
        """
        self.logger.info(
            f"MESSAGE_SENT | case_id={case_id} | channel={channel} | "
            f"msg_id={message_id} | length={message_length}"
        )

    def log_escalation(
        self,
        case_id: int,
        manager_id: int,
        reason: str,
        urgency: str = "normal",
    ) -> None:
        """Log escalation event.

        Args:
            case_id: Case identifier
            manager_id: Assigned manager ID
            reason: Escalation reason
            urgency: Urgency level
        """
        self.logger.warning(
            f"ESCALATION | case_id={case_id} | manager={manager_id} | "
            f"urgency={urgency} | reason={reason}"
        )

    def log_compensation_offered(
        self,
        case_id: int,
        amount: int,
        reason: str,
    ) -> None:
        """Log compensation offer event.

        Args:
            case_id: Case identifier
            amount: Compensation amount in rubles
            reason: Reason for compensation
        """
        self.logger.info(
            f"COMPENSATION_OFFERED | case_id={case_id} | "
            f"amount={amount}₽ | reason={reason}"
        )

    def log_case_resolved(
        self,
        case_id: int,
        resolution: str,
        final_rating: Optional[int] = None,
    ) -> None:
        """Log case resolution event.

        Args:
            case_id: Case identifier
            resolution: Resolution type
            final_rating: Final rating if changed
        """
        msg = f"CASE_RESOLVED | case_id={case_id} | resolution={resolution}"
        if final_rating is not None:
            msg += f" | final_rating={final_rating}⭐"
        self.logger.info(msg)

    def log_error(
        self,
        case_id: int,
        node: str,
        error: str,
        traceback: Optional[str] = None,
    ) -> None:
        """Log error event.

        Args:
            case_id: Case identifier
            node: Node where error occurred
            error: Error message
            traceback: Optional traceback
        """
        self.logger.error(
            f"ERROR | case_id={case_id} | node={node} | error={error}"
        )
        if traceback:
            self.logger.debug(f"Traceback: {traceback}")

    def log_llm_call(
        self,
        case_id: int,
        model: str,
        tokens_in: int,
        tokens_out: int,
        duration_ms: int,
    ) -> None:
        """Log LLM call metrics.

        Args:
            case_id: Case identifier
            model: Model name
            tokens_in: Input tokens
            tokens_out: Output tokens
            duration_ms: Call duration in milliseconds
        """
        self.logger.debug(
            f"LLM_CALL | case_id={case_id} | model={model} | "
            f"tokens={tokens_in}→{tokens_out} | duration={duration_ms}ms"
        )


# Global event logger instance
event_logger = EventLogger()


class MetricsCollector:
    """Collect and report metrics for 5STARS operations."""

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: dict[str, Any] = {
            "cases_processed": 0,
            "cases_escalated": 0,
            "cases_resolved": 0,
            "total_compensation": 0,
            "average_response_time_ms": 0,
            "reviews_improved": 0,
        }
        self._response_times: list[int] = []

    def record_case_processed(self) -> None:
        """Record a processed case."""
        self.metrics["cases_processed"] += 1

    def record_case_escalated(self) -> None:
        """Record an escalated case."""
        self.metrics["cases_escalated"] += 1

    def record_case_resolved(self) -> None:
        """Record a resolved case."""
        self.metrics["cases_resolved"] += 1

    def record_compensation(self, amount: int) -> None:
        """Record compensation amount."""
        self.metrics["total_compensation"] += amount

    def record_response_time(self, duration_ms: int) -> None:
        """Record response time."""
        self._response_times.append(duration_ms)
        if self._response_times:
            self.metrics["average_response_time_ms"] = (
                sum(self._response_times) / len(self._response_times)
            )

    def record_review_improved(self) -> None:
        """Record an improved review (rating increased)."""
        self.metrics["reviews_improved"] += 1

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics."""
        return {
            **self.metrics,
            "timestamp": datetime.utcnow().isoformat(),
            "escalation_rate": (
                self.metrics["cases_escalated"] / self.metrics["cases_processed"]
                if self.metrics["cases_processed"] > 0
                else 0
            ),
            "resolution_rate": (
                self.metrics["cases_resolved"] / self.metrics["cases_processed"]
                if self.metrics["cases_processed"] > 0
                else 0
            ),
        }


# Global metrics collector instance
metrics = MetricsCollector()
