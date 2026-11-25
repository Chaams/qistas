from __future__ import annotations

from .base import BaseJudge, JudgeError


class GeminiJudge(BaseJudge):
    provider = "gemini"

    def __init__(self, model: str, client=None):
        super().__init__(model)
        if client is None:
            try:
                from google import genai
            except ImportError as e:
                raise JudgeError("pip install qistas[gemini]") from e
            client = genai.Client()
        self.client = client

    def _complete(self, system: str, prompt: str) -> tuple[str, int, int]:
        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={"system_instruction": system, "temperature": 0, "response_mime_type": "application/json"},
        )
        u = resp.usage_metadata
        return resp.text or "", u.prompt_token_count or 0, u.candidates_token_count or 0
