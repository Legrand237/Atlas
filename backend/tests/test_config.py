"""Tests de la configuration (lecture depuis l'environnement, validation)."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_defaults_when_environment_is_empty(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.environment == "development"
    assert settings.log_level == "INFO"


def test_values_are_read_from_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    settings = Settings(_env_file=None)

    assert settings.environment == "production"
    assert settings.log_level == "WARNING"


def test_invalid_environment_fails_fast(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging-inconnu")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_invalid_log_level_fails_fast(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "BAVARD")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
