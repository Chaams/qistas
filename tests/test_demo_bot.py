"""Offline tests of the example bot (no API key: generation is injected)."""
import importlib.util
import json
import threading
import urllib.request
from pathlib import Path

DEMO = Path(__file__).resolve().parents[1] / "examples" / "arabic-rag-demo"


def load():
    spec = importlib.util.spec_from_file_location("demo_bot", DEMO / "bot.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_retrieve_finds_fee_document():
    bot = load()
    docs = bot.retrieve("ابي اعرف رسوم التحويل الدولي", k=2)
    assert any("التحويل الدولي" in d["text"] for d in docs)


def test_retrieve_handles_diacritics_and_hamza():
    bot = load()
    assert bot.retrieve("المُرابَحة", k=1)[0]["id"] == bot.retrieve("المرابحه", k=1)[0]["id"]


def test_answer_passes_sources_and_history_to_generator():
    bot = load()
    seen = {}

    def fake_generate(system, messages):
        seen["system"], seen["messages"] = system, messages
        return "الرسوم 25 درهم", {"input_tokens": 10, "output_tokens": 5}

    out = bot.answer([{"role": "user", "content": "كم رسوم التحويل الدولي؟"}], generate=fake_generate)
    assert out["answer"] == "الرسوم 25 درهم"
    assert out["sources"] and all(isinstance(s, str) for s in out["sources"])
    assert "<documents>" in seen["messages"][-1]["content"]
    assert out["usage"]["input_tokens"] == 10


def test_http_server_roundtrip():
    bot = load()
    bot.GENERATE = lambda system, messages: ("مرحبا", {"input_tokens": 1, "output_tokens": 1})
    server = bot.make_server(0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    try:
        assert urllib.request.urlopen(f"http://127.0.0.1:{port}/health").status == 200
        req = urllib.request.Request(f"http://127.0.0.1:{port}/chat", method="POST",
                                     data=json.dumps({"messages": [{"role": "user", "content": "سلام"}]}).encode(),
                                     headers={"Content-Type": "application/json"})
        body = json.loads(urllib.request.urlopen(req).read())
        assert body["answer"] == "مرحبا" and "sources" in body
    finally:
        server.shutdown()


def test_gemini_requires_model(monkeypatch):
    import pytest

    monkeypatch.setenv("DEMO_PROVIDER", "gemini")
    monkeypatch.delenv("DEMO_MODEL", raising=False)
    with pytest.raises(RuntimeError, match="DEMO_MODEL"):
        load().pick_generator()


def test_gemini_message_conversion():
    bot = load()
    contents = bot.to_gemini([{"role": "user", "content": "سلام"}, {"role": "assistant", "content": "أهلا"},
                              {"role": "user", "content": "كم الرسوم؟"}])
    assert [c["role"] for c in contents] == ["user", "model", "user"]
    assert contents[2]["parts"] == [{"text": "كم الرسوم؟"}]


def test_no_cost_for_unpriced_model(monkeypatch):
    monkeypatch.setenv("DEMO_MODEL", "some-free-model")
    bot = load()
    out = bot.answer([{"role": "user", "content": "سلام"}], generate=lambda s, m: ("x", {"input_tokens": 1, "output_tokens": 1}))
    assert "cost_usd" not in out["usage"]


def test_gemini_bot_is_deterministic(monkeypatch):
    """Temperature 0: a bot under test in CI must answer the same way run after run."""
    import sys
    import types

    seen = {}

    class FakeModels:
        def generate_content(self, model, contents, config):
            seen.update(config)
            return types.SimpleNamespace(text="رد", usage_metadata=None)

    fake = types.ModuleType("google.genai")
    fake.Client = lambda: types.SimpleNamespace(models=FakeModels())
    monkeypatch.setitem(sys.modules, "google.genai", fake)
    monkeypatch.setitem(sys.modules, "google", types.SimpleNamespace(genai=fake))
    monkeypatch.setenv("DEMO_MODEL", "m")
    load().gemini_generate("sys", [{"role": "user", "content": "x"}])
    assert seen["temperature"] == 0
