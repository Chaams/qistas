from __future__ import annotations

import json
import time
from typing import Any

import httpx

from ..cases import Turn
from ..config import HttpTarget
from ..jsonpath import get_path
from .base import BotReply, as_context


def _render(template: Any, history: list[dict], last_user: str) -> Any:
    if template == "{{turns}}":
        return history
    if isinstance(template, str):
        return template.replace("{{last_user}}", last_user)
    if isinstance(template, dict):
        return {k: _render(v, history, last_user) for k, v in template.items()}
    if isinstance(template, list):
        return [_render(v, history, last_user) for v in template]
    return template


class HttpBot:
    def __init__(self, cfg: HttpTarget, client: httpx.Client | None = None):
        self.cfg = cfg
        self.client = client or httpx.Client(timeout=cfg.timeout_s)

    def wait_healthy(self) -> None:
        if not self.cfg.health_url:
            return
        deadline = time.monotonic() + self.cfg.health_timeout_s
        while True:
            try:
                if self.client.get(self.cfg.health_url, timeout=2).status_code < 500:
                    return
            except httpx.HTTPError:
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Bot not healthy at {self.cfg.health_url} after {self.cfg.health_timeout_s}s")
            time.sleep(min(1.0, max(0.05, deadline - time.monotonic())))

    def _call(self, history: list[dict], last_user: str) -> tuple[dict | None, str | None]:
        body = _render(self.cfg.body, history, last_user)
        try:
            resp = self.client.request(self.cfg.method, self.cfg.url, headers=self.cfg.headers, json=body)
        except httpx.TimeoutException:
            return None, f"Timeout after {self.cfg.timeout_s}s"
        except httpx.HTTPError as e:
            return None, f"Request failed: {e}"
        if resp.status_code >= 400:
            return None, f"HTTP {resp.status_code}: {resp.text[:200]}"
        try:
            return resp.json(), None
        except (json.JSONDecodeError, ValueError):
            return None, "Response is not JSON"

    def ask(self, turns: list[Turn]) -> BotReply:
        history: list[dict] = []
        start = time.perf_counter()
        data: dict | None = None
        answer = ""
        for turn in turns:
            history.append({"role": "user", "content": turn.user})
            data, err = self._call(list(history), turn.user)
            if err:
                return BotReply("", usage={"transcript": history}, latency_ms=_ms(start), error=err)
            try:
                answer = str(get_path(data, self.cfg.answer_path))
            except KeyError:
                return BotReply("", usage={"transcript": history}, latency_ms=_ms(start),
                                error=f"answer_path not found in response: {self.cfg.answer_path}")
            history.append({"role": "assistant", "content": answer})
        usage: dict = {"transcript": history}
        context = None
        try:
            if self.cfg.context_path:
                context = as_context(get_path(data, self.cfg.context_path))
            if self.cfg.usage_path:
                usage["bot"] = get_path(data, self.cfg.usage_path)
        except KeyError as e:
            return BotReply(answer, usage=usage, latency_ms=_ms(start), error=f"path not found in response: {e.args[0]}")
        return BotReply(answer, context=context, usage=usage, latency_ms=_ms(start))


def _ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000
