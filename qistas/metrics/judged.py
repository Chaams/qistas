"""Quality metrics scored by the LLM judge, with lexical fallback when no judge is configured."""
from __future__ import annotations

from ..cases import Case
from ..judge import JudgeError
from ..targets import BotReply
from . import lexical
from .base import MetricResult


def _ask(name: str, judge, task: str, payload: dict) -> MetricResult:
    try:
        r = judge.score(task, payload)
    except JudgeError as e:
        return MetricResult(name, None, reason="judge error", error=str(e))
    return MetricResult(name, r.score, reason=r.reason, cost_usd=r.cost_usd)


def _question(case: Case) -> str:
    return case.turns[-1].user


def faithfulness(case: Case, reply: BotReply, judge) -> MetricResult:
    context = case.context or reply.context
    if not context:
        return MetricResult("faithfulness", None, reason="no context")
    if judge is None:
        s = lexical.faithfulness(reply.answer, context)
        return MetricResult("faithfulness", s, reason=f"{lexical.OFFLINE}recouvrement {s:.2f}")
    return _ask("faithfulness", judge, "faithfulness", {"answer": reply.answer, "context": context})


def hallucination_rate(case: Case, reply: BotReply, judge) -> MetricResult:
    f = faithfulness(case, reply, judge)
    score = None if f.score is None else 1.0 - f.score
    return MetricResult("hallucination_rate", score, reason=f.reason, cost_usd=f.cost_usd, error=f.error)


def answer_relevance(case: Case, reply: BotReply, judge) -> MetricResult:
    if not case.reference:
        return MetricResult("answer_relevance", None, reason="no reference")
    if judge is None:
        s = lexical.answer_relevance(reply.answer, case.reference)
        return MetricResult("answer_relevance", s, reason=f"{lexical.OFFLINE}recouvrement {s:.2f}")
    payload = {"question": _question(case), "answer": reply.answer, "reference": case.reference}
    return _ask("answer_relevance", judge, "answer_relevance", payload)


def dialect_match(case: Case, reply: BotReply, judge) -> MetricResult:
    if not case.expected_dialect:
        return MetricResult("dialect_match", None, reason="no expected dialect")
    if judge is None:
        s, why = lexical.dialect_score(reply.answer, case.expected_dialect)
        return MetricResult("dialect_match", s, reason=lexical.OFFLINE + why)
    payload = {"answer": reply.answer, "expected_dialect": case.expected_dialect, "question": _question(case)}
    return _ask("dialect_match", judge, "dialect_match", payload)
