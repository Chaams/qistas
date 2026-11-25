from __future__ import annotations

from .base import SCHEMA, BaseJudge, JudgeError


class AnthropicJudge(BaseJudge):
    """Claude judge.

    The current Claude API rejects `temperature`, so consistency comes from structured outputs
    (strict JSON schema) and low effort instead.
    """

    provider = "anthropic"

    def __init__(self, model: str, client=None):
        super().__init__(model)
        if client is None:
            try:
                import anthropic
            except ImportError as e:
                raise JudgeError("pip install qistas[anthropic]") from e
            client = anthropic.Anthropic()
        self.client = client

    def _complete(self, system: str, prompt: str) -> tuple[str, int, int]:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        )
        if resp.stop_reason == "refusal":
            raise JudgeError("Judge model refused to evaluate this case")
        text = "".join(b.text for b in resp.content if b.type == "text")
        return text, resp.usage.input_tokens, resp.usage.output_tokens
