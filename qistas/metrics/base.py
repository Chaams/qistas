from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MetricResult:
    name: str
    score: float | None
    passed: bool | None = None  # set for binary (attack / pii) checks
    reason: str = ""
    cost_usd: float | None = None
    error: str | None = None
