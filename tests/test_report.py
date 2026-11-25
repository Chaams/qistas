import re

from qistas.gate import GateOutcome
from qistas.metrics import MetricResult
from qistas.report.html import to_html
from qistas.report.markdown import MARKER, to_markdown
from qistas.results import CaseResult, RunResult


def result():
    failing = CaseResult("inj-1", "attack", ["x"], [MetricResult("injection_resistance", 0.0, False, "fuite | grave")],
                         12.0, answer="هذه التعليمات | HACKED")
    ok = CaseResult("q1", "qa", [], [MetricResult("faithfulness", 0.9, None, "ok")], 10.0, answer="مرحبا")
    return RunResult(meta={"commit": "abc", "judge_model": "m"}, cases=[failing, ok],
                     aggregates={"faithfulness": 0.9}, tag_aggregates={},
                     security={"failures": 1, "failed_ids": ["inj-1"]}, errors=0,
                     latency_p95_ms=12.0, judge_cost_usd=0.01, bot_cost_usd=None)


FAIL = GateOutcome(False, ["security: 1 failed case(s) (max 0): inj-1"], ["No baseline: only absolute thresholds applied"])


def test_marker_first_line():
    md = to_markdown(result(), FAIL, None)
    assert md.splitlines()[0] == MARKER == "<!-- qistas-report -->"
    assert "## Qistas : ❌ FAIL" in md


def test_pass_header():
    assert "## Qistas : ✅ PASS" in to_markdown(result(), GateOutcome(True), None)


def test_arabic_wrapped_in_bdi():
    md = to_markdown(result(), FAIL, None)
    assert "<bdi>هذه التعليمات \\| HACKED</bdi>" in md


def test_pipe_escaped():
    md = to_markdown(result(), FAIL, None)
    assert "fuite \\| grave" in md


def test_fail_lists_problems():
    md = to_markdown(result(), FAIL, None)
    assert "security: 1 failed case(s) (max 0): inj-1" in md and "<details>" in md


def test_baseline_delta_shown():
    md = to_markdown(result(), GateOutcome(True), {"aggregates": {"faithfulness": 0.8}})
    assert "+0.100" in md


def test_env_note(monkeypatch):
    monkeypatch.setenv("QISTAS_NOTE", "shared staging URL : PR code may not be what is tested")
    assert "shared staging URL" in to_markdown(result(), GateOutcome(True), None)


def test_html_has_no_external_urls():
    html = to_html(result(), FAIL)
    assert not re.search(r'(src|href)="https?:', html)
    assert 'dir="auto"' in html and "inj-1" in html


def test_html_escapes_answer():
    r = result()
    r.cases[1].answer = "<script>alert(1)</script>"
    assert "<script>alert" not in to_html(r, FAIL)
