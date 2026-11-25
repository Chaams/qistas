"""PR comment (GitHub-flavoured Markdown)."""
from __future__ import annotations

import html
import os
import re

from ..gate import GateOutcome
from ..results import CaseResult, RunResult

MARKER = "<!-- qistas-report -->"
_ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")
MAX_ANSWER = 300


def cell(text: object) -> str:
    """Make any value safe inside a Markdown table cell; isolate Arabic runs for RTL."""
    s = html.escape(str(text), quote=False).replace("|", "\\|").replace("\r", " ").replace("\n", " ")
    return f"<bdi>{s}</bdi>" if _ARABIC.search(s) else s


def _num(v: float | None) -> str:
    return "—" if v is None else f"{v:.3f}"


def _failing(cases: list[CaseResult]) -> list[tuple[CaseResult, str, str]]:
    rows = []
    for c in cases:
        if c.error:
            rows.append((c, "—", f"error: {c.error}"))
        for m in c.metrics:
            if m.error:
                rows.append((c, m.name, f"error: {m.error}"))
            elif m.passed is False:
                rows.append((c, m.name, m.reason))
    return rows


def to_markdown(result: RunResult, outcome: GateOutcome, baseline: dict | None,
                thresholds: dict[str, float] | None = None) -> str:
    thresholds = thresholds or {}
    base = (baseline or {}).get("aggregates", {})
    lines = [MARKER, f"## Qistas : {'✅ PASS' if outcome.passed else '❌ FAIL'}", ""]

    lines += ["| Métrique | Valeur | Baseline | Δ | Seuil |", "|---|---|---|---|---|"]
    for name, value in result.aggregates.items():
        b = base.get(name)
        delta = "—" if b is None else f"{value - b:+.3f}"
        lines.append(f"| {cell(name)} | {_num(value)} | {_num(b)} | {delta} | {thresholds.get(name, '—')} |")
    lines.append(f"| sécurité (échecs) | {result.security['failures']} | — | — | 0 |")
    lines.append(f"| latence p95 (ms) | {result.latency_p95_ms:.0f} | {_num((baseline or {}).get('latency_p95_ms'))} | — | — |")
    lines.append(f"| coût juge (USD) | {_num(result.judge_cost_usd)} | — | — | — |")
    if result.bot_cost_usd is not None:
        lines.append(f"| coût bot (USD) | {_num(result.bot_cost_usd)} | — | — | — |")
    lines.append("")

    if outcome.problems:
        lines += ["### Problèmes", *[f"- {cell(p)}" for p in outcome.problems], ""]

    failing = _failing(result.cases)
    if failing:
        lines += [f"<details><summary>{len(failing)} cas en échec</summary>", "",
                  "| Cas | Type | Métrique | Raison | Réponse du bot |", "|---|---|---|---|---|"]
        for c, metric, reason in failing:
            answer = c.answer if len(c.answer) <= MAX_ANSWER else c.answer[:MAX_ANSWER] + "…"
            lines.append(f"| {cell(c.id)} | {c.type} | {cell(metric)} | {cell(reason)} | {cell(answer)} |")
        lines += ["", "</details>", ""]

    notes = list(outcome.notes)
    if os.environ.get("QISTAS_NOTE"):
        notes.append(os.environ["QISTAS_NOTE"])
    if result.meta.get("judge_provider") == "recorded":
        notes.append("Judge answers were replayed from recorded cassettes, not computed live.")
    if notes:
        lines += ["### Notes", *[f"- {cell(n)}" for n in notes], ""]

    meta = result.meta
    lines.append(f"<sub>Qistas {meta.get('qistas_version', '')} · juge {meta.get('judge_model') or 'hors ligne'} · "
                 f"commit {str(meta.get('commit') or '')[:7]} · {len(result.cases)} cas</sub>")
    return "\n".join(lines) + "\n"
