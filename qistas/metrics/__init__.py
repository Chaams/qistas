"""Metric registry: name -> fn(case, reply, judge | None) -> MetricResult."""
from __future__ import annotations

from typing import Callable

from .base import MetricResult
from .judged import answer_relevance, dialect_match, faithfulness, hallucination_rate
from .script import script_consistency
from .security import injection_resistance, pii_leak

REGISTRY: dict[str, Callable[..., MetricResult]] = {
    "faithfulness": faithfulness,
    "hallucination_rate": hallucination_rate,
    "answer_relevance": answer_relevance,
    "dialect_match": dialect_match,
    "script_consistency": script_consistency,
    "injection_resistance": injection_resistance,
    "pii_leak": pii_leak,
}

__all__ = ["MetricResult", "REGISTRY"]
