"""Example Arabic RAG bot for the Qistas demo — a FICTIONAL bank ("Nakhla Demo Bank").

Retrieval: lexical (Arabic-normalized BM25) over corpus.json. Generation: Claude.
HTTP: GET /health ; POST /chat {"messages": [{"role", "content"}...]}
      -> {"answer", "sources": [text...], "usage": {"input_tokens", "output_tokens", "cost_usd"}}

Run:  ANTHROPIC_API_KEY=... python examples/arabic-rag-demo/bot.py   (port 8000, or $PORT)
"""
from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
CORPUS = json.loads((HERE / "corpus.json").read_text(encoding="utf-8"))
PROVIDER = os.environ.get("DEMO_PROVIDER", "anthropic")  # anthropic | gemini (Gemini API free tier)
MODEL = os.environ.get("DEMO_MODEL") or ("claude-opus-5-5" if PROVIDER == "anthropic" else "")
PRICES = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50)}

_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"})
_STOP = {"في", "من", "علي", "الي", "عن", "ما", "هل", "كم", "او", "و", "ان", "لا", "هو", "هي", "ابي", "اعرف"}


def _tokens(text: str) -> list[str]:
    text = _DIACRITICS.sub("", unicodedata.normalize("NFC", text)).translate(_MAP).lower()
    out = []
    for t in re.findall(r"[^\W_]+", text):
        if t.startswith("ال") and len(t) > 4:  # strip the article so «التحويل» matches «تحويل»
            t = t[2:]
        if t not in _STOP:
            out.append(t)
    return out


_DOCS = [(d, Counter(_tokens(d["title"] + " " + d["text"]))) for d in CORPUS]
_AVG = sum(sum(c.values()) for _, c in _DOCS) / len(_DOCS)
_DF = Counter(t for _, c in _DOCS for t in c)


def retrieve(query: str, k: int = 3) -> list[dict]:
    """BM25 over the corpus; returns the top-k documents."""
    q = _tokens(query)
    n = len(_DOCS)
    scored = []
    for doc, tf in _DOCS:
        length = sum(tf.values())
        s = 0.0
        for t in q:
            if t in tf:
                idf = math.log(1 + (n - _DF[t] + 0.5) / (_DF[t] + 0.5))
                s += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (0.25 + 0.75 * length / _AVG))
        scored.append((s, doc))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:k]]


def system_prompt() -> str:
    return (HERE / "system_prompt.txt").read_text(encoding="utf-8")


def claude_generate(system: str, messages: list[dict]) -> tuple[str, dict]:
    import anthropic

    client = anthropic.Anthropic()
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=system,
        messages=messages,
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        return "عذرًا، لا أستطيع المساعدة في هذا الطلب.", _usage(resp.usage)
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    return text, _usage(resp.usage)


def _usage(u) -> dict:
    return {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens}


def to_gemini(messages: list[dict]) -> list[dict]:
    return [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages]


def gemini_generate(system: str, messages: list[dict]) -> tuple[str, dict]:
    import time

    from google import genai

    client = genai.Client()
    for delay in [2, 4, 8, 16, 32, None]:  # free tier: wait for the per-minute quota on 429
        try:
            resp = client.models.generate_content(
                model=MODEL, contents=to_gemini(messages),
                config={"system_instruction": system, "max_output_tokens": 1000},
            )
            break
        except Exception as e:
            if getattr(e, "code", None) not in (429, 503) or delay is None:
                raise
            time.sleep(delay)
    u = resp.usage_metadata
    usage = {"input_tokens": (u.prompt_token_count or 0) if u else 0,
             "output_tokens": (u.candidates_token_count or 0) if u else 0}
    return (resp.text or "").strip(), usage


def pick_generator():
    if PROVIDER == "gemini":
        if not MODEL:
            raise RuntimeError("DEMO_MODEL is required with DEMO_PROVIDER=gemini (model id from Google AI Studio)")
        return gemini_generate
    return claude_generate


GENERATE = None  # set by tests; otherwise chosen from DEMO_PROVIDER


def answer(messages: list[dict], generate=None) -> dict:
    generate = generate or GENERATE or pick_generator()
    last = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    docs = retrieve(" ".join(m["content"] for m in messages if m["role"] == "user")[-500:] or last)
    context = "\n".join(f'<doc title="{d["title"]}">{d["text"]}</doc>' for d in docs)
    turn = f"<documents>\n{context}\n</documents>\n\n{last}"
    text, usage = generate(system_prompt(), [*messages[:-1], {"role": "user", "content": turn}])
    price = PRICES.get(MODEL)
    if price:
        usage["cost_usd"] = (usage["input_tokens"] * price[0] + usage["output_tokens"] * price[1]) / 1_000_000
    return {"answer": text, "sources": [d["text"] for d in docs], "usage": usage}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        self._send(200 if self.path == "/health" else 404, {"ok": self.path == "/health"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/chat":
            return self._send(404, {"error": "not found"})
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            self._send(200, answer(data["messages"]))
        except Exception as e:  # demo server: report the error to the caller
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, *args) -> None:
        pass


def make_server(port: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    pick_generator()  # fail fast on a missing DEMO_MODEL
    print(f"Nakhla demo bot on http://127.0.0.1:{port} ({PROVIDER} / {MODEL})")
    make_server(port).serve_forever()
