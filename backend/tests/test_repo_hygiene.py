"""Tests d'hygiène du dépôt : aucun secret ne doit pouvoir arriver dans Git."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = REPO_ROOT / "backend" / ".env.example"
SENSITIVE_NAME = re.compile(r"KEY|SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIAL", re.IGNORECASE)


def _parse_env_example() -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name, _, value = line.partition("=")
        values[name.strip()] = value.strip()
    return values


def test_env_example_exists():
    assert ENV_EXAMPLE.is_file()


def test_env_example_has_no_value_for_sensitive_names():
    for name, value in _parse_env_example().items():
        if SENSITIVE_NAME.search(name):
            assert value == "", f"{name} ne doit pas avoir de valeur dans .env.example"


def test_env_example_has_no_secret_looking_values():
    suspicious = re.compile(r"sk-[A-Za-z0-9]{10,}|ghp_[A-Za-z0-9]{10,}|AKIA[A-Z0-9]{12,}")
    assert not suspicious.search(ENV_EXAMPLE.read_text(encoding="utf-8"))


def _git_check_ignore(relative_path: str) -> bool | None:
    """True si ignoré, False si non ignoré, None si Git ou le dépôt est indisponible."""
    if shutil.which("git") is None or not (REPO_ROOT / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "check-ignore", "-q", relative_path],
        cwd=REPO_ROOT,
        check=False,
    )
    return result.returncode == 0


@pytest.mark.parametrize(
    "path",
    ["backend/.env", ".env", "backend/.env.local", "secrets/cle.txt", "server.pem", "backend/.venv/x"],
)
def test_sensitive_paths_are_gitignored(path):
    ignored = _git_check_ignore(path)
    if ignored is None:
        pytest.skip("Git ou dépôt .git indisponible")
    assert ignored, f"{path} devrait être ignoré par Git"


def test_env_example_is_not_gitignored():
    ignored = _git_check_ignore("backend/.env.example")
    if ignored is None:
        pytest.skip("Git ou dépôt .git indisponible")
    assert not ignored
