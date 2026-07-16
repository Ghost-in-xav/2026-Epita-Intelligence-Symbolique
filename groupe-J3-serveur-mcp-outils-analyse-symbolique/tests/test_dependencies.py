"""Tests de coherence des manifestes de dependances."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_rdflib_is_declared_in_all_dependency_manifests():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert '"rdflib>=' in pyproject
    assert "rdflib>=" in requirements


def test_dotenv_is_declared_in_all_dependency_manifests():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert '"python-dotenv>=' in pyproject
    assert "python-dotenv>=" in requirements


def test_env_example_documents_gemini_configuration():
    example_path = ROOT / ".env.example"
    assert example_path.is_file()
    example = example_path.read_text(encoding="utf-8")

    assert "GEMINI_API_KEY=" in example
    assert "GEMINI_MODEL=gemini-2.5-flash" in example


def test_local_env_files_are_ignored():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert ".env" in gitignore
    assert ".env.local" in gitignore
    assert ".env.*.local" in gitignore
