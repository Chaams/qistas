"""The gate: decide whether a run may ship."""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import GateConfig
from .results import RunResult

HIGHER_IS_BETTER = {"faithfulness", "answer_relevance", "dialect_match", "script_consistency"}
LOWER_IS_BETTER = {"hallucination_rate", "latency_p95_ms", "judge_cost_usd"}


@dataclass
class GateOutcome:
    passed: bool
    problems: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _check_threshold(name: str, value: float | None, limit: float, scope: str = "") -> str | None:
    where = f" [{scope}]" if scope else ""
    if value is None:
        return f"{name}{where}: no value, threshold {limit}"
    if name in LOWER_IS_BETTER:
        return f"{name}{where}: {value:.3f} > max {limit}" if value > limit else None
    return f"{name}{where}: {value:.3f} < min {limit}" if value < limit else None


def _regressions(cand: dict, base: dict, cfg: GateConfig, notes: list[str]) -> list[str]:
    """Port of Chaams/llmops-eval-pipeline `regressions()`, extended to absent metrics."""
    problems = []
    for name in sorted(HIGHER_IS_BETTER | LOWER_IS_BETTER):
        c, b = cand.get(name), base.get(name)
        if c is None or b is None:
            if (c is None) != (b is None):
                notes.append(f"{name}: absent from {'run' if c is None else 'baseline'}, not compared")
            continue
        tol = cfg.latency_tolerance if name == "latency_p95_ms" else cfg.tolerance
        if name in HIGHER_IS_BETTER and c < b * (1 - tol):
            problems.append(f"{name}: {c:.3f} regresses vs baseline {b:.3f} (tolerance {tol:.0%})")
        if name in LOWER_IS_BETTER and c > b * (1 + tol):
            problems.append(f"{name}: {c:.3f} regresses vs baseline {b:.3f} (tolerance {tol:.0%})")
    return problems


def _flat(r: RunResult | dict) -> dict:
    if isinstance(r, RunResult):
        return {**r.aggregates, "latency_p95_ms": r.latency_p95_ms, "judge_cost_usd": r.judge_cost_usd}
    return {**r.get("aggregates", {}), "latency_p95_ms": r.get("latency_p95_ms"), "judge_cost_usd": r.get("judge_cost_usd")}


def evaluate(result: RunResult, baseline: dict | None, cfg: GateConfig) -> GateOutcome:
    problems: list[str] = []
    notes: list[str] = []

    if result.errors:
        problems.append(f"{result.errors} case(s) ended in error (bot or judge): results are incomplete")

    sec = result.security
    if sec["failures"] > cfg.max_failures:
        problems.append(f"security: {sec['failures']} failed case(s) (max {cfg.max_failures}): {', '.join(sec['failed_ids'])}")

    flat = _flat(result)
    for name, limit in cfg.thresholds.items():
        if (p := _check_threshold(name, flat.get(name), limit)):
            problems.append(p)
    for tag, limits in cfg.tag_thresholds.items():
        aggs = result.tag_aggregates.get(tag, {})
        for name, limit in limits.items():
            if (p := _check_threshold(name, aggs.get(name), limit, scope=tag)):
                problems.append(p)

    if baseline is None:
        notes.append("No baseline: only absolute thresholds applied")
    else:
        problems.extend(_regressions(flat, _flat(baseline), cfg, notes))

    return GateOutcome(not problems, problems, notes)
