"""`results.json` model (schema 1)."""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .metrics import MetricResult

SCHEMA = 1


@dataclass
class CaseResult:
    id: str
    type: str
    tags: list[str]
    metrics: list[MetricResult]
    latency_ms: float
    error: str | None = None
    transcript: list[dict] = field(default_factory=list)
    answer: str = ""

    @property
    def has_error(self) -> bool:
        return self.error is not None or any(m.error for m in self.metrics)


@dataclass
class RunResult:
    meta: dict
    cases: list[CaseResult]
    aggregates: dict[str, float]
    tag_aggregates: dict[str, dict[str, float]]
    security: dict
    errors: int
    latency_p95_ms: float
    judge_cost_usd: float | None
    bot_cost_usd: float | None
    schema: int = SCHEMA

    def to_dict(self) -> dict:
        return asdict(self)

    def write(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def from_dict(cls, d: dict) -> "RunResult":
        if d.get("schema") != SCHEMA:
            raise ValueError(f"Unsupported results schema: {d.get('schema')} (expected {SCHEMA})")
        cases = [CaseResult(**{**c, "metrics": [MetricResult(**m) for m in c["metrics"]]}) for c in d["cases"]]
        return cls(**{**d, "cases": cases})

    @classmethod
    def read(cls, path: str | Path) -> "RunResult":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def p95(values: list[float]) -> float:
    """Nearest-rank 95th percentile."""
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]
