"""Configuration partagee de l'hote Gemini et du harnais d'evaluation."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ENV = PROJECT_ROOT / ".env"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
_CONFIG_KEYS = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL")
_dotenv_values: dict[str, str | None] = {}
_system_keys: set[str] = set()


def load_project_env(path: Path | None = None) -> None:
    """Charge un fichier dotenv sans ecraser l'environnement du processus."""
    global _dotenv_values

    for key, loaded_value in _dotenv_values.items():
        if (
            key not in _system_keys
            and loaded_value is not None
            and os.environ.get(key) == loaded_value
        ):
            os.environ.pop(key, None)

    for key in _CONFIG_KEYS:
        current = os.environ.get(key)
        if current and current != _dotenv_values.get(key):
            _system_keys.add(key)

    env_path = path or PROJECT_ENV
    _dotenv_values = dict(dotenv_values(env_path))
    load_dotenv(env_path, override=False)


def _system_value(key: str) -> str | None:
    current = os.environ.get(key)
    if not current:
        return None
    if key in _system_keys or current != _dotenv_values.get(key):
        return current
    return None


def gemini_api_key() -> str | None:
    """Resout la cle Gemini en respectant la priorite systeme puis dotenv."""
    return (
        _system_value("GEMINI_API_KEY")
        or _system_value("GOOGLE_API_KEY")
        or _dotenv_values.get("GEMINI_API_KEY")
        or _dotenv_values.get("GOOGLE_API_KEY")
    )


def gemini_model() -> str:
    """Resout le modele Gemini configure, avec un repli stable."""
    return (
        _system_value("GEMINI_MODEL")
        or _dotenv_values.get("GEMINI_MODEL")
        or DEFAULT_GEMINI_MODEL
    )


load_project_env()
