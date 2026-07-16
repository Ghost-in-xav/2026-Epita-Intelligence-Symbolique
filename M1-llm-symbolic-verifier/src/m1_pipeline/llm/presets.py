"""Provider presets for the OpenAI-compatible client.

Switching backend "a la volee" is just a matter of pointing the same OpenAI
client at a different ``base_url`` + ``model`` + API key. Each preset records:

* ``base_url``    : the OpenAI-compatible endpoint
* ``api_key_env`` : which environment variable holds the key (None => no key)
* ``default_model``

Add a provider by adding one line here, or bypass presets entirely with
``--base-url`` / ``--api-key-env`` on the CLI.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Preset:
    name: str
    base_url: str | None
    api_key_env: str | None
    default_model: str
    model_env: str | None = None  # optional override env var


PRESETS: dict[str, Preset] = {
    # OpenAI native.
    "openai": Preset(
        name="openai",
        base_url=None,  # SDK default (https://api.openai.com/v1)
        api_key_env="OPENAI_API_KEY",
        default_model="gpt-4o-mini",
        model_env="M1_OPENAI_MODEL",
    ),
    # Anthropic via its OpenAI-compatible endpoint.
    "anthropic": Preset(
        name="anthropic",
        base_url="https://api.anthropic.com/v1/",
        api_key_env="ANTHROPIC_API_KEY",
        default_model="claude-sonnet-4-6",
        model_env="M1_ANTHROPIC_MODEL",
    ),
    # Local Ollama (no API key required).
    "ollama": Preset(
        name="ollama",
        base_url="http://localhost:11434/v1",
        api_key_env=None,
        default_model="llama3.1",
        model_env="M1_OLLAMA_MODEL",
    ),
    # OpenRouter aggregator.
    "openrouter": Preset(
        name="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        default_model="anthropic/claude-sonnet-4",
        model_env="M1_OPENROUTER_MODEL",
    ),
    # Generic local OpenAI-compatible server (vLLM, llama.cpp, LM Studio, ...).
    "local": Preset(
        name="local",
        base_url="http://localhost:8000/v1",
        api_key_env=None,
        default_model="local-model",
        model_env="M1_LOCAL_MODEL",
    ),
}


def list_presets() -> list[Preset]:
    return list(PRESETS.values())
