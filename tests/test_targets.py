import json

import httpx
import pytest
import respx

from qistas.cases import Turn
from qistas.config import HttpTarget, PythonTarget
from qistas.jsonpath import get_path
from qistas.targets import make_target

URL = "https://bot.example/chat"


def http(**kw):
    base = dict(url=URL, answer_path="data.answer", context_path="data.docs", body={"messages": "{{turns}}", "q": "{{last_user}}"})
    base.update(kw)
    return make_target(HttpTarget(**base))


def test_get_path():
    assert get_path({"a": {"b": [{"c": 1}]}}, "a.b[0].c") == 1
    with pytest.raises(KeyError):
        get_path({"a": {}}, "a.x")


@respx.mock
def test_http_extracts_answer_and_context():
    respx.post(URL).respond(json={"data": {"answer": "مرحبا", "docs": ["d1"]}})
    r = http().ask([Turn(user="سلام")])
    assert r.answer == "مرحبا" and r.context == ["d1"] and r.error is None and r.latency_ms >= 0


@respx.mock
def test_http_500_sets_error():
    respx.post(URL).respond(500, text="boom")
    r = http().ask([Turn(user="x")])
    assert r.error.startswith("HTTP 500")


@respx.mock
def test_http_html_body_sets_error():
    respx.post(URL).respond(200, text="<html>oops</html>")
    assert http().ask([Turn(user="x")]).error == "Response is not JSON"


@respx.mock
def test_http_missing_answer_path():
    respx.post(URL).respond(json={"data": {}})
    assert "data.answer" in http().ask([Turn(user="x")]).error


@respx.mock
def test_http_timeout_sets_error():
    respx.post(URL).mock(side_effect=httpx.ReadTimeout("slow"))
    assert "timeout" in http().ask([Turn(user="x")]).error.lower()


@respx.mock
def test_multi_turn_sends_history():
    route = respx.post(URL)
    route.side_effect = [
        httpx.Response(200, json={"data": {"answer": "أهلا"}}),
        httpx.Response(200, json={"data": {"answer": "تمام"}}),
    ]
    r = http(context_path=None).ask([Turn(user="سلام"), Turn(user="كيفك")])
    second = json.loads(route.calls[1].request.content)
    assert second["messages"] == [
        {"role": "user", "content": "سلام"},
        {"role": "assistant", "content": "أهلا"},
        {"role": "user", "content": "كيفك"},
    ]
    assert second["q"] == "كيفك"
    assert r.answer == "تمام" and len(r.usage["transcript"]) == 4


@respx.mock
def test_usage_path_extracted():
    respx.post(URL).respond(json={"data": {"answer": "x"}, "usage": {"cost_usd": 0.01}})
    r = http(context_path=None, usage_path="usage").ask([Turn(user="x")])
    assert r.usage["bot"] == {"cost_usd": 0.01}


def test_python_target_calls_function():
    r = make_target(PythonTarget(callable="tests.fixtures.echo_bot:ask")).ask([Turn(user="سلام")])
    assert r.answer == "رد: سلام" and r.context == ["وثيقة"]


def test_python_target_exception_sets_error():
    r = make_target(PythonTarget(callable="tests.fixtures.echo_bot:missing")).ask([Turn(user="x")])
    assert r.error and "missing" in r.error


def test_wait_healthy_times_out():
    t = http(health_url="http://127.0.0.1:9/health", health_timeout_s=0.2)
    with pytest.raises(TimeoutError):
        t.wait_healthy()
