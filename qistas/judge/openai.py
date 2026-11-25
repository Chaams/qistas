from __future__ import annotations

from .base import BaseJudge, JudgeError


class OpenAIJudge(BaseJudge):
    provider = "openai"

    def __init__(self, model: str, client=None):
        super().__init__(model)
        if client is None:
            try:
                import openai
            except ImportError as e:
                raise JudgeError("pip install qistas[openai]") from e
            client = openai.OpenAI()
        self.client = client

    def _complete(self, system: str, prompt: str) -> tuple[str, int, int]:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content or "", resp.usage.prompt_tokens, resp.usage.completion_tokens
