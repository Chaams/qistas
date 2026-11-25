"""Run every case against the bot, score it, aggregate."""
from __future__ import annotations

import os
import subprocess
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import __version__
from .cases import Case
from .config import QistasConfig
from .judge.base import cost_usd
from .metrics import REGISTRY, MetricResult
from .results import CaseResult, RunResult, p95


def _commit() -> str | None:
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _score_case(case: Case, target, judge) -> tuple[CaseResult, dict]:
    reply = target.ask(case.turns)
    transcript = reply.usage.get("transcript", [])
    if reply.error:
        return CaseResult(case.id, case.type, case.tags, [], reply.latency_ms, reply.error, transcript), reply.usage
    metrics: list[MetricResult] = []
    for name in case.effective_metrics():
        fn = REGISTRY.get(name)
        if fn is None:
            metrics.append(MetricResult(name, None, error=f"Unknown metric: {name}"))
            continue
        metrics.append(fn(case, reply, judge))
    return CaseResult(case.id, case.type, case.tags, metrics, reply.latency_ms, None, transcript, reply.answer), reply.usage


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _aggregate(results: list[CaseResult]) -> dict[str, float]:
    buckets: dict[str, list[float]] = defaultdict(list)
    for r in results:
        if r.type != "qa":
            continue
        for m in r.metrics:
            if m.score is not None and m.error is None:
                buckets[m.name].append(m.score)
    return {k: _mean(v) for k, v in sorted(buckets.items())}


def _sum_or_none(values: list[float | None]) -> float | None:
    if not values or any(v is None for v in values):
        return None
    return sum(values)  # type: ignore[arg-type]


def _judge_cost(judge, results: list[CaseResult]) -> float | None:
    """Sum of judge costs; None without a judge or when the judge model has no known price."""
    if judge is None or cost_usd(getattr(judge, "provider", ""), getattr(judge, "model", ""), 0, 0) is None:
        return None
    return sum(m.cost_usd for r in results for m in r.metrics if m.cost_usd is not None)


def run(cfg: QistasConfig, cases: list[Case], target, judge, concurrency: int = 4) -> RunResult:
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        scored = list(pool.map(lambda c: _score_case(c, target, judge), cases))
    results = [r for r, _ in scored]

    tags: dict[str, list[CaseResult]] = defaultdict(list)
    for r in results:
        for t in r.tags:
            tags[t].append(r)

    failed = [r.id for r in results if r.type in ("attack", "pii") and any(m.passed is False for m in r.metrics)]
    usage_path = getattr(cfg.target, "usage_path", None)
    bot_cost = None
    if usage_path:
        bot_cost = _sum_or_none([(u.get("bot") or {}).get("cost_usd") if isinstance(u.get("bot"), dict) else None
                                 for r, u in scored if r.error is None])

    return RunResult(
        meta={
            "commit": _commit(),
            "judge_provider": getattr(judge, "provider", None),
            "judge_model": getattr(judge, "model", None),
            "started_at": started,
            "qistas_version": __version__,
        },
        cases=results,
        aggregates=_aggregate(results),
        tag_aggregates={t: _aggregate(rs) for t, rs in sorted(tags.items())},
        security={"failures": len(failed), "failed_ids": failed},
        errors=sum(r.has_error for r in results),
        latency_p95_ms=p95([r.latency_ms for r in results if r.error is None]),
        judge_cost_usd=_judge_cost(judge, results),
        bot_cost_usd=bot_cost,
    )
