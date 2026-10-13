"""Tests de la configuration de la passerelle IA (valeurs par défaut, validation, secret)."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def _settings(**values) -> Settings:
    return Settings(_env_file=None, **values)


def test_defaults_are_unconfigured():
    settings = _settings()
    assert settings.gemini_api_key is None
    assert [settings.model_for_tier(t) for t in ("simple", "medium", "hard")] == [None, None, None]
    assert settings.llm_daily_request_limit == 200
    assert settings.llm_daily_token_limit == 200000
    assert settings.llm_max_output_tokens == 1024
    assert settings.llm_timeout_seconds == 30.0


def test_empty_values_mean_not_configured():
    settings = _settings(gemini_api_key="  ", llm_model_simple="", llm_model_hard="  ")
    assert settings.gemini_api_key is None
    assert settings.llm_model_simple is None and settings.llm_model_hard is None


def test_values_are_read_and_key_stays_secret():
    settings = _settings(gemini_api_key="secret-de-test-123", llm_model_medium="un-modele_1.5")
    assert settings.gemini_api_key.get_secret_value() == "secret-de-test-123"
    assert "secret-de-test-123" not in repr(settings) and "secret-de-test-123" not in str(settings)
    assert settings.model_for_tier("medium") == "un-modele_1.5"


@pytest.mark.parametrize("bad", ["a/b", "../x", "a b", "x?y=1", "-debut", "é"])
def test_invalid_model_names_are_refused(bad):
    with pytest.raises(ValidationError):
        _settings(llm_model_simple=bad)


@pytest.mark.parametrize(
    "values",
    [
        {"llm_daily_request_limit": 0},
        {"llm_daily_token_limit": 10},
        {"llm_max_output_tokens": 5},
        {"llm_max_output_tokens": 100000},
        {"llm_timeout_seconds": 1},
    ],
)
def test_out_of_range_limits_fail_fast(values):
    with pytest.raises(ValidationError):
        _settings(**values)
