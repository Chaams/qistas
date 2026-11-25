from qistas.baseline import baseline_from
from qistas.config import GateConfig
from qistas.gate import evaluate
from qistas.results import RunResult


def result(aggregates=None, tags=None, failures=0, failed_ids=None, errors=0, p95=100.0, cost=None):
    return RunResult(
        meta={"commit": "abc"}, cases=[], aggregates=aggregates or {}, tag_aggregates=tags or {},
        security={"failures": failures, "failed_ids": failed_ids or []}, errors=errors,
        latency_p95_ms=p95, judge_cost_usd=cost, bot_cost_usd=None,
    )


def test_single_security_failure_blocks_despite_good_average():
    out = evaluate(result({"faithfulness": 0.99}, failures=1, failed_ids=["inj-001"]), None, GateConfig())
    assert not out.passed and any("inj-001" in p for p in out.problems)


def test_max_failures_relaxes():
    assert evaluate(result(failures=1, failed_ids=["x"]), None, GateConfig(max_failures=1)).passed


def test_threshold_failure_message():
    out = evaluate(result({"faithfulness": 0.80}), None, GateConfig(thresholds={"faithfulness": 0.85}))
    assert not out.passed
    assert "faithfulness" in out.problems[0] and "0.800" in out.problems[0] and "0.85" in out.problems[0]


def test_lower_is_better_threshold():
    out = evaluate(result({"hallucination_rate": 0.2}), None, GateConfig(thresholds={"hallucination_rate": 0.1}))
    assert not out.passed


def test_threshold_on_missing_metric_is_problem():
    out = evaluate(result({}), None, GateConfig(thresholds={"faithfulness": 0.85}))
    assert not out.passed and "faithfulness" in out.problems[0]


def test_tag_threshold():
    r = result({"faithfulness": 0.95}, tags={"banking": {"faithfulness": 0.88}})
    out = evaluate(r, None, GateConfig(tag_thresholds={"banking": {"faithfulness": 0.9}}))
    assert not out.passed and "banking" in out.problems[0]


def test_regression_beyond_tolerance_fails():
    base = baseline_from(result({"faithfulness": 0.90}))
    assert not evaluate(result({"faithfulness": 0.881}), base, GateConfig()).passed


def test_regression_within_tolerance_passes():
    base = baseline_from(result({"faithfulness": 0.90}))
    assert evaluate(result({"faithfulness": 0.883}), base, GateConfig()).passed


def test_latency_regression_fails():
    base = baseline_from(result(p95=100.0))
    out = evaluate(result(p95=150.0), base, GateConfig())
    assert not out.passed and "latency_p95_ms" in out.problems[0]


def test_metric_missing_on_one_side_is_noted():
    base = baseline_from(result({"dialect_match": 0.9}))
    out = evaluate(result({"faithfulness": 0.9}), base, GateConfig())
    assert out.passed and any("dialect_match" in n for n in out.notes)


def test_no_baseline_note():
    out = evaluate(result({"faithfulness": 0.9}), None, GateConfig())
    assert out.passed and "No baseline: only absolute thresholds applied" in out.notes


def test_errors_block():
    out = evaluate(result(errors=2), None, GateConfig())
    assert not out.passed and "2" in out.problems[0]


def test_baseline_shape():
    b = baseline_from(result({"faithfulness": 0.9}, cost=0.5))
    assert set(b) == {"schema", "meta", "aggregates", "tag_aggregates", "latency_p95_ms", "judge_cost_usd"}
