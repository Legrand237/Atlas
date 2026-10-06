"""Tests de la couche base de données (étape 2a)."""

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.db import (
    DatabaseNotConfigured,
    DatabaseUnavailable,
    build_engine,
    check_connection,
    get_engine,
)


def test_database_url_defaults_to_none(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert Settings(_env_file=None).database_url is None


def test_empty_database_url_means_not_configured(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "   ")
    assert Settings(_env_file=None).database_url is None


@pytest.mark.parametrize("scheme", ["postgresql", "postgres"])
def test_provider_url_is_converted_to_psycopg(monkeypatch, scheme):
    monkeypatch.setenv("DATABASE_URL", f"{scheme}://u:p@h.example/db?sslmode=require")
    url = Settings(_env_file=None).database_url.get_secret_value()
    assert url == "postgresql+psycopg://u:p@h.example/db?sslmode=require"


def test_non_postgres_url_is_rejected(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql://u:p@h/db")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_database_url_is_hidden_in_repr(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:SECRETPW@h/db")
    assert "SECRETPW" not in repr(Settings(_env_file=None))


def test_get_engine_without_configuration_fails_clearly(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr("app.db.get_settings", lambda: Settings(_env_file=None))
    get_engine.cache_clear()
    with pytest.raises(DatabaseNotConfigured):
        get_engine()
    get_engine.cache_clear()


def test_check_connection_runs_a_real_query_on_local_sqlite():
    # SQLite local : vérifie la logique de check_connection, PAS PostgreSQL.
    engine = build_engine("sqlite://")
    assert "sqlite" in check_connection(engine)


def test_unreachable_postgres_raises_without_leaking_password():
    # Port 1 : aucune base n'écoute, la connexion échoue réellement et vite.
    engine = build_engine("postgresql+psycopg://u:SECRETPW@127.0.0.1:1/db", connect_timeout=2)
    with pytest.raises(DatabaseUnavailable) as info:
        check_connection(engine)
    assert "SECRETPW" not in str(info.value)
    assert "127.0.0.1" not in str(info.value)
