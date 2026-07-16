"""Deterministic, offline providers.

These never hit the network. They let the whole pipeline (strategies, verifier,
re-prompt loop, evaluation) run and be unit-tested without an API key, and they
make the "rejection then correction" behaviour reproducible.
"""
from __future__ import annotations

import json

from .base import LLMResponse, Message


class ScriptedProvider:
    """Replays a fixed list of responses, one per ``complete`` call.

    Used in unit tests to drive exact generate -> verify -> reprompt sequences.
    """

    name = "scripted"

    def __init__(self, responses: list[str], model: str = "scripted-1"):
        self.model = model
        self._responses = list(responses)
        self._i = 0

    def complete(self, messages: list[Message], *, system=None, temperature=0.0, max_tokens=1536) -> LLMResponse:
        if self._i >= len(self._responses):
            text = self._responses[-1] if self._responses else "{}"
        else:
            text = self._responses[self._i]
            self._i += 1
        return LLMResponse(text=text, model=self.model, provider=self.name)


class OracleProvider:
    """Solves the bound problem with Z3, optionally failing the first attempts.

    Implements the optional ``bind`` capability (ProblemAware). ``fail_first``
    controls how many initial attempts return a deliberately wrong answer, so the
    re-prompt loop and its metrics can be exercised deterministically.
    """

    name = "mock"

    def __init__(self, model: str = "oracle-z3", fail_first: int = 0):
        self.model = model
        self.fail_first = fail_first
        self._problem = None
        self._calls = 0

    def bind(self, problem) -> None:
        self._problem = problem
        self._calls = 0

    def complete(self, messages: list[Message], *, system=None, temperature=0.0, max_tokens=1536) -> LLMResponse:
        from ..verifier import solve  # lazy import to avoid cycle at import time

        self._calls += 1
        if self._problem is None:
            return LLMResponse(text="{}", model=self.model, provider=self.name)

        if self._calls <= self.fail_first:
            # Deliberately broken answer to trigger a rejection.
            wrong = {name: 0 for name in self._problem.variable_names()}
            text = "ANSWER: " + json.dumps(wrong)
            return LLMResponse(text=text, model=self.model, provider=self.name)

        model = solve(self._problem)
        payload = model if model is not None else {}
        text = "ANSWER: " + json.dumps(payload)
        return LLMResponse(text=text, model=self.model, provider=self.name)
