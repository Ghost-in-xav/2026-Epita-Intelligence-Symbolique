"""The one and only network backend: an OpenAI-compatible Chat Completions client.

Every real provider (OpenAI, Anthropic, Ollama, OpenRouter, vLLM, ...) speaks the
same wire format, so we keep a single implementation and only vary base_url /
api_key / model. That is exactly the "swap provider on the fly" property asked
for: same code, different endpoint.
"""
from __future__ import annotations

import os

from .base import LLMError, LLMResponse, Message
from .presets import PRESETS, Preset


class OpenAICompatibleProvider:
    """Talks to any OpenAI-compatible endpoint via the official ``openai`` SDK."""

    def __init__(
        self,
        *,
        name: str,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        api_key_env: str | None = None,
    ):
        self.name = name
        self.model = model
        self._base_url = base_url
        self._api_key_env = api_key_env
        self._api_key = api_key
        self._client = None

    @classmethod
    def from_preset(cls, preset: Preset, model: str | None = None) -> "OpenAICompatibleProvider":
        chosen = model
        if chosen is None and preset.model_env:
            chosen = os.environ.get(preset.model_env)
        chosen = chosen or preset.default_model
        return cls(
            name=preset.name,
            model=chosen,
            base_url=preset.base_url,
            api_key_env=preset.api_key_env,
        )

    def _resolve_api_key(self) -> str:
        if self._api_key:
            return self._api_key
        if self._api_key_env:
            key = os.environ.get(self._api_key_env)
            if key:
                return key
        # Endpoints without auth (Ollama / local) still want a non-empty string.
        return "not-needed"

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - import guard
            raise LLMError("openai SDK not installed (uv sync)") from exc
        self._client = OpenAI(api_key=self._resolve_api_key(), base_url=self._base_url)
        return self._client

    def complete(
        self,
        messages: list[Message],
        *,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1536,
    ) -> LLMResponse:
        client = self._ensure_client()
        payload = []
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend({"role": m.role, "content": m.content} for m in messages)
        try:
            resp = client.chat.completions.create(
                model=self.model,
                messages=payload,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:  # pragma: no cover - network path
            raise LLMError(f"{self.name} request failed: {exc}") from exc
        text = resp.choices[0].message.content or ""
        usage = getattr(resp, "usage", None)
        return LLMResponse(
            text=text,
            model=self.model,
            provider=self.name,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
        )


__all__ = ["OpenAICompatibleProvider", "PRESETS"]
