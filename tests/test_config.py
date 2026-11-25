import pytest

from qistas.config import HttpTarget, load_config

CFG = """
target:
  kind: http
  url: https://bot.example/chat
  headers:
    Authorization: "Bearer ${BOT_TOKEN}"
  body: {messages: "{{turns}}"}
  answer_path: answer
judge:
  provider: anthropic
gate:
  thresholds: {faithfulness: 0.85}
"""


def write(tmp_path, text):
    p = tmp_path / "qistas.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_env_interpolation(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "abc")
    cfg = load_config(write(tmp_path, CFG))
    assert isinstance(cfg.target, HttpTarget)
    assert cfg.target.headers["Authorization"] == "Bearer abc"
    assert cfg.gate.tolerance == 0.02 and cfg.gate.max_failures == 0
    assert cfg.cases == ["qistas/cases"]


def test_missing_env_var_message(tmp_path, monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    with pytest.raises(ValueError, match="Missing environment variable: BOT_TOKEN"):
        load_config(write(tmp_path, CFG))


def test_unknown_key_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "abc")
    with pytest.raises(ValueError):
        load_config(write(tmp_path, CFG + "\nunknown: 1\n"))


def test_python_target(tmp_path):
    cfg = load_config(write(tmp_path, "target: {kind: python, callable: 'm:f'}\n"))
    assert cfg.target.callable == "m:f"
    assert cfg.judge.provider == "anthropic"
