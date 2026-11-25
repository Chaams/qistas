"""Tiny in-process bot used by tests: echoes the last user message."""


def ask(question, history=None):
    return {"answer": f"رد: {question}", "context": ["وثيقة"]}
