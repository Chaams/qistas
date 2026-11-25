from __future__ import annotations

import time

from .base import BaseJudge, JudgeError

RATE_LIMIT_CODES = {429, 503}
BACKOFF_S = [2, 4, 8, 16, 32]  # ~1 minute in total: enough for a per-minute free-tier quota to refill


class GeminiJudge(BaseJudge):
    """Gemini judge (works on the Gemini API free tier, with retries on rate limits)."""

    provider = "gemini"

    def __init__(self, model: str, client=None, sleep=time.sleep):
        super().__init__(model)
        if client is None:
            try:
                from google import genai
            except ImportError as e:
                raise JudgeError("pip install qistas[gemini]") from e
            client = genai.Client()
        self.client = client
        self.sleep = sleep

    def _call(self, system: str, prompt: str):
        for delay in [*BACKOFF_S, None]:
            try:
                return self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={"system_instruction": system, "temperature": 0, "response_mime_type": "application/json"},
                )
            except Exception as e:
                if getattr(e, "code", None) not in RATE_LIMIT_CODES or delay is None:
                    raise
                self.sleep(delay)

    def _complete(self, system: str, prompt: str) -> tuple[str, int, int]:
        resp = self._call(system, prompt)
        u = resp.usage_metadata
        tin = (u.prompt_token_count or 0) if u else 0
        tout = (u.candidates_token_count or 0) if u else 0
        return resp.text or "", tin, tout
