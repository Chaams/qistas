"""Baseline = the aggregates of a reference run, versioned in the user's repo."""
from __future__ import annotations

import json
from pathlib import Path

from .results import SCHEMA, RunResult


def baseline_from(result: RunResult) -> dict:
    return {
        "schema": SCHEMA,
        "meta": result.meta,
        "aggregates": result.aggregates,
        "tag_aggregates": result.tag_aggregates,
        "latency_p95_ms": result.latency_p95_ms,
        "judge_cost_usd": result.judge_cost_usd,
    }


def load_baseline(path: str | Path) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"Unsupported baseline schema: {data.get('schema')} (expected {SCHEMA})")
    return data


def write_baseline(result: RunResult, path: str | Path) -> None:
    Path(path).write_text(json.dumps(baseline_from(result), ensure_ascii=False, indent=2), encoding="utf-8")
