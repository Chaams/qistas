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
