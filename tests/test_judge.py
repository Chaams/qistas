import json
from types import SimpleNamespace as NS

import pytest

from qistas.config import JudgeConfig
from qistas.judge import JudgeError, make_judge
from qistas.judge.anthropic import AnthropicJudge
from qistas.judge.base import BaseJudge, cost_usd
from qistas.judge.openai import OpenAIJudge
from qistas.judge.recorded import RecordedJudge, RecordingJudge


class FakeJudge(BaseJudge):
    provider = "fake"

    def __init__(self, replies, model="m"):
        super().__init__(model)
        self.replies = list(replies)
        self.calls = 0

    def _complete(self, system, prompt):
        self.calls += 1
        return self.replies.pop(0), 10, 5


def test_parses_score_and_reason():
    r = FakeJudge(['{"score": 0.8, "reason": "ok"}']).score("faithfulness", {"answer": "a"})
    assert (r.score, r.reason, r.input_tokens, r.output_tokens) == (0.8, "ok", 10, 5)


def test_invalid_json_retries_once_then_errors():
    j = FakeJudge(["nope", "still nope"])
    with pytest.raises(JudgeError):
        j.score("faithfulness", {})
    assert j.calls == 2


def test_retry_recovers():
    j = FakeJudge(["nope", '{"score": 1, "reason": "r"}'])
    assert j.score("faithfulness", {}).score == 1.0 and j.calls == 2


def test_out_of_range_score_errors():
    with pytest.raises(JudgeError):
        FakeJudge(['{"score": 1.5, "reason": "x"}'] * 2).score("faithfulness", {})


def test_unknown_task_rejected():
    with pytest.raises(ValueError):
        FakeJudge([]).score("nope", {})


def test_gemini_requires_model():
    with pytest.raises(JudgeError, match="judge.model is required for provider gemini"):
        make_judge(JudgeConfig(provider="gemini"))


def test_unknown_model_cost_is_none():
    assert cost_usd("anthropic", "made-up-model", 1000, 1000) is None


def test_known_model_cost_computed():
    assert cost_usd("anthropic", "claude-sonnet-5-5", 1_000_000, 1_000_000) == pytest.approx(12.0)


class _Recorder:
    def __init__(self, response):
        self.kwargs = None
        self.response = response

    def create(self, **kw):
        self.kwargs = kw
        return self.response


def test_anthropic_request_shape():
    resp = NS(content=[NS(type="text", text='{"score": 0.5, "reason": "r"}')],
              usage=NS(input_tokens=3, output_tokens=4), stop_reason="end_turn")
    rec = _Recorder(resp)
    j = AnthropicJudge("claude-sonnet-5-5", client=NS(messages=rec))
    r = j.score("dialect_match", {"answer": "x", "expected_dialect": "gulf"})
    assert r.score == 0.5 and r.cost_usd is not None
    assert "temperature" not in rec.kwargs  # rejected by the current Claude API
    assert rec.kwargs["output_config"]["format"]["type"] == "json_schema"


def test_anthropic_refusal_is_error():
    resp = NS(content=[], usage=NS(input_tokens=1, output_tokens=0), stop_reason="refusal")
    j = AnthropicJudge("claude-sonnet-5-5", client=NS(messages=_Recorder(resp)))
    with pytest.raises(JudgeError, match="refus"):
        j.score("faithfulness", {})


def test_openai_temperature_zero():
    resp = NS(choices=[NS(message=NS(content='{"score": 1, "reason": "r"}'))],
              usage=NS(prompt_tokens=1, completion_tokens=1))
    rec = _Recorder(resp)
    j = OpenAIJudge("some-model", client=NS(chat=NS(completions=rec)))
    j.score("faithfulness", {})
    assert rec.kwargs["temperature"] == 0


def test_recording_then_replay(tmp_path):
    inner = FakeJudge(['{"score": 0.7, "reason": "rec"}'])
    RecordingJudge(inner, tmp_path).score("faithfulness", {"answer": "أ"})
    replay = RecordedJudge(tmp_path)
    assert replay.score("faithfulness", {"answer": "أ"}).score == 0.7
    with pytest.raises(JudgeError, match="No recorded"):
        replay.score("faithfulness", {"answer": "other"})
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1 and "أ" in files[0].read_text(encoding="utf-8")
