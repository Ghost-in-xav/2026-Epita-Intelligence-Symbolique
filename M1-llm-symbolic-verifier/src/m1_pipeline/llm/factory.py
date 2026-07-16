"""Build a provider from a name (preset), a raw URL, or the offline mock."""
from __future__ import annotations

from .base import LLMProvider
from .client import OpenAICompatibleProvider
from .mock import OracleProvider
from .presets import PRESETS


def make_provider(
    provider: str = "anthropic",
    *,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    api_key_env: str | None = None,
    mock_fail_first: int = 0,
) -> LLMProvider:
    """Return an :class:`LLMProvider`.

    ``provider`` is either:
      * ``"mock"``         -> offline Z3 oracle (no network, no key),
      * a preset name      -> one of :data:`PRESETS` (openai, anthropic, ...),
      * a raw ``http(s)://`` URL -> ad-hoc OpenAI-compatible endpoint.

    ``base_url`` / ``api_key`` / ``api_key_env`` override the preset, so any
    endpoint can be reached without editing presets.
    """
    if provider == "mock":
        return OracleProvider(fail_first=mock_fail_first)

    # Raw endpoint passed directly as the provider string.
    if provider.startswith("http://") or provider.startswith("https://"):
        return OpenAICompatibleProvider(
            name="custom",
            model=model or "local-model",
            base_url=provider,
            api_key=api_key,
            api_key_env=api_key_env,
        )

    if provider in PRESETS:
        prov = OpenAICompatibleProvider.from_preset(PRESETS[provider], model=model)
        # Allow per-call overrides on top of the preset.
        if base_url is not None:
            prov._base_url = base_url
        if api_key is not None:
            prov._api_key = api_key
        if api_key_env is not None:
            prov._api_key_env = api_key_env
        return prov

    raise ValueError(
        f"unknown provider {provider!r}; choose one of "
        f"{['mock', *PRESETS.keys()]} or pass an http(s):// base URL"
    )
