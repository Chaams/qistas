import json

import pytest

from qistas.cases import Case
from qistas.config import QistasConfig
from qistas.results import RunResult, p95
from qistas.runner import run
from qistas.targets import BotReply


class ScriptedBot:
    """Returns canned replies keyed by the last user message."""

    def __init__(self, replies):
        self.replies = replies

    def ask(self, turns):
        r = self.replies[turns[-1].user]
        return r if isinstance(r, BotReply) else BotReply(r, latency_ms=10)

    def wait_healthy(self):
        pass


CFG = QistasConfig.model_validate({"target": {"kind": "python", "callable": "m:f"}})


def case(cid, user, **kw):
    return Case.model_validate({"id": cid, "turns": [{"user": user}], **kw})


def test_aggregates_ignore_none():
    cases = [
        case("q1", "a", reference="الرسوم 25 درهم", context=["الرسوم 25 درهم"], tags=["bank"]),
        case("q2", "b", reference=None),  # answer_relevance -> None, faithfulness -> None
    ]
    bot = ScriptedBot({"a": "الرسوم 25 درهم", "b": "شي"})
    res = run(CFG, cases, bot, judge=None)
    assert res.aggregates["faithfulness"] == 1.0
    assert res.aggregates["answer_relevance"] == 1.0
    assert res.tag_aggregates["bank"]["faithfulness"] == 1.0
    assert [c.id for c in res.cases] == ["q1", "q2"]


def test_security_failures_collected():
    cases = [
        Case.model_validate({"id": "a1", "type": "attack", "turns": [{"user": "x"}],
                             "expect": {"must_not_contain": ["HACKED"]}}),
        Case.model_validate({"id": "a2", "type": "attack", "turns": [{"user": "y"}],
                             "expect": {"must_not_contain": ["HACKED"]}}),
    ]
    res = run(CFG, cases, ScriptedBot({"x": "HACKED", "y": "لا"}), judge=None)
    assert res.security == {"failures": 1, "failed_ids": ["a1"]}


def test_bot_error_counted_and_run_continues():
    cases = [case("q1", "a", reference="x"), case("q2", "b", reference="x"), case("q3", "c", reference="x")]
    bot = ScriptedBot({"a": "x", "b": BotReply("", error="HTTP 500: boom"), "c": "x"})
    res = run(CFG, cases, bot, judge=None)
    assert res.errors == 1
    assert res.cases[1].error == "HTTP 500: boom" and res.cases[1].metrics == []
    assert res.aggregates["answer_relevance"] == 1.0


def test_metric_error_counts_as_error():
    class BadJudge:
        provider, model = "x", "x"

        def score(self, task, payload):
            from qistas.judge import JudgeError
            raise JudgeError("bad json")

    res = run(CFG, [case("q1", "a", reference="x")], ScriptedBot({"a": "x"}), judge=BadJudge())
    assert res.errors == 1


def test_p95_latency():
    assert p95([float(i) for i in range(1, 101)]) == 95.0
    assert p95([]) == 0.0


def test_unknown_metric_is_error():
    res = run(CFG, [case("q1", "a", metrics=["nope"])], ScriptedBot({"a": "x"}), judge=None)
    assert res.cases[0].metrics[0].error == "Unknown metric: nope"


def test_judge_cost_none_when_unknown():
    res = run(CFG, [case("q1", "a")], ScriptedBot({"a": "x"}), judge=None)
    assert res.judge_cost_usd is None and res.bot_cost_usd is None


def test_roundtrip_json_utf8(tmp_path):
    res = run(CFG, [case("q1", "سلام", reference="مرحبا")], ScriptedBot({"سلام": "مرحبا"}), judge=None)
    out = tmp_path / "results.json"
    res.write(out)
    raw = out.read_text(encoding="utf-8")
    assert "مرحبا" in raw and "\\u" not in raw
    back = RunResult.read(out)
    assert back.schema == 1 and back.cases[0].transcript == res.cases[0].transcript
    assert json.loads(raw)["meta"]["qistas_version"]


def test_judge_cost_sums_judged_metrics_only():
    from qistas.judge import JudgeResult

    class PricedJudge:
        provider, model = "anthropic", "claude-sonnet-5-5"

        def score(self, task, payload):
            return JudgeResult(1.0, "ok", 0.002, 10, 10)

    c = case("q1", "a", reference="x", context=["x"], expected_dialect="gulf")
    res = run(CFG, [c], ScriptedBot({"a": "x"}), judge=PricedJudge())
    # faithfulness + answer_relevance + dialect_match are judged; script_consistency is not
    assert res.judge_cost_usd == pytest.approx(0.006)


def test_unexpected_metric_exception_does_not_crash_run():
    class Crash:
        provider, model = "x", "x"

        def score(self, task, payload):
            raise RuntimeError("provider SDK bug")

    res = run(CFG, [case("q1", "a", reference="x"), case("q2", "b", reference="x")],
              ScriptedBot({"a": "x", "b": "x"}), judge=Crash())
    assert res.errors == 2
    assert any("provider SDK bug" in (m.error or "") for m in res.cases[0].metrics)
