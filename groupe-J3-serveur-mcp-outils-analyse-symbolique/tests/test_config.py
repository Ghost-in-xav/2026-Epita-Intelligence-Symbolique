"""Tests de chargement de la configuration Gemini depuis un fichier .env."""

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
_CONFIG_KEYS = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_MODEL")


def _read_config(env_file: Path, system_env: dict[str, str] | None = None) -> dict:
    env = os.environ.copy()
    for key in _CONFIG_KEYS:
        env.pop(key, None)
    env.update(system_env or {})
    env["PYTHONPATH"] = str(ROOT / "src")
    code = (
        "import json, sys; from pathlib import Path; "
        "from symbolic_mcp.config import load_project_env, gemini_api_key, gemini_model; "
        "load_project_env(Path(sys.argv[1])); "
        "print(json.dumps({'api_key': gemini_api_key(), 'model': gemini_model()}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code, str(env_file)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _read_host(env_file: Path, system_env: dict[str, str] | None = None) -> dict:
    env = os.environ.copy()
    for key in _CONFIG_KEYS:
        env.pop(key, None)
    env.update(system_env or {})
    env["PYTHONPATH"] = str(ROOT / "src")
    code = (
        "import json, sys; from pathlib import Path; "
        "from symbolic_mcp.config import load_project_env; "
        "load_project_env(Path(sys.argv[1])); "
        "from symbolic_mcp.host.gemini_host import GeminiMCPHost; "
        "host = GeminiMCPHost(); "
        "print(json.dumps({'api_key': host._api_key, 'model': host.model}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code, str(env_file)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_loads_gemini_configuration_from_dotenv(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GEMINI_API_KEY=file-key\nGEMINI_MODEL=file-model\n", encoding="utf-8"
    )

    assert _read_config(env_file) == {"api_key": "file-key", "model": "file-model"}


def test_system_environment_has_priority_over_dotenv(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GEMINI_API_KEY=file-key\nGEMINI_MODEL=file-model\n", encoding="utf-8"
    )

    result = _read_config(
        env_file,
        {"GEMINI_API_KEY": "system-key", "GEMINI_MODEL": "system-model"},
    )

    assert result == {"api_key": "system-key", "model": "system-model"}


def test_gemini_api_key_has_priority_over_google_alias(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")

    result = _read_config(
        env_file,
        {"GEMINI_API_KEY": "gemini-key", "GOOGLE_API_KEY": "google-key"},
    )

    assert result["api_key"] == "gemini-key"


def test_system_google_alias_has_priority_over_dotenv_gemini_key(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=file-key\n", encoding="utf-8")

    result = _read_config(env_file, {"GOOGLE_API_KEY": "system-google-key"})

    assert result["api_key"] == "system-google-key"


def test_gemini_host_uses_centralized_dotenv_configuration(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GEMINI_API_KEY=file-key\nGEMINI_MODEL=file-model\n", encoding="utf-8"
    )

    assert _read_host(env_file) == {"api_key": "file-key", "model": "file-model"}


def test_gemini_host_preserves_system_alias_priority(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=file-key\n", encoding="utf-8")

    result = _read_host(env_file, {"GOOGLE_API_KEY": "system-google-key"})

    assert result["api_key"] == "system-google-key"


def test_reloading_dotenv_replaces_values_loaded_from_previous_file(tmp_path):
    first_env = tmp_path / "first.env"
    second_env = tmp_path / "second.env"
    first_env.write_text(
        "GEMINI_API_KEY=first-key\nGEMINI_MODEL=first-model\n", encoding="utf-8"
    )
    second_env.write_text(
        "GEMINI_API_KEY=second-key\nGEMINI_MODEL=second-model\n", encoding="utf-8"
    )
    env = os.environ.copy()
    for key in _CONFIG_KEYS:
        env.pop(key, None)
    env["PYTHONPATH"] = str(ROOT / "src")
    code = (
        "import json, sys; from pathlib import Path; "
        "from symbolic_mcp.config import load_project_env, gemini_api_key, gemini_model; "
        "load_project_env(Path(sys.argv[1])); load_project_env(Path(sys.argv[2])); "
        "print(json.dumps({'api_key': gemini_api_key(), 'model': gemini_model()}))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code, str(first_env), str(second_env)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "api_key": "second-key",
        "model": "second-model",
    }
