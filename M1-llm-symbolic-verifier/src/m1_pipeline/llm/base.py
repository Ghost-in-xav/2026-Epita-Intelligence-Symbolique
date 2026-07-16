"""Provider-agnostic LLM interface.

Every backend (Anthropic, OpenAI, Ollama, mock) implements :class:`LLMProvider`.
The rest of the pipeline only ever sees this interface, so the generator can be
swapped at runtime without touching the pipeline / strategies / evaluation code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class Message:
    """A single chat turn. ``role`` is ``"user"`` or ``"assistant"``."""

    role: str
    content: str


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    # Token accounting when the backend reports it (best effort).
    input_tokens: int | None = None
    output_tokens: int | None = None
    raw: dict = field(default_factory=dict)


class LLMProvider(Protocol):
    """Minimal contract a generator backend must satisfy."""

    name: str
    model: str

    def complete(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1536,
    ) -> LLMResponse:
        ...


@runtime_checkable
class ProblemAware(Protocol):
    """Optional capability.

    Offline/deterministic providers (mock, oracle) need to know which problem
    they are answering. The pipeline calls :meth:`bind` before the attempt loop
    when the provider implements it; real API providers do not, and so remain
    pure text-in / text-out.
    """

    def bind(self, problem) -> None:  # noqa: ANN001 - avoid import cycle
        ...


class LLMError(RuntimeError):
    """Raised when a backend cannot be reached or returns an error."""
