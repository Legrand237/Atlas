"""Tests de POST /llm/chat et du service, sur une VRAIE base PostgreSQL (schéma temporaire).

Le fournisseur est remplacé par un double de test (``FakeProvider``) : ces tests vérifient NOTRE logique
(authentification, niveaux, plafonds, audit, correspondance des erreurs), pas Google. Sans DATABASE_URL, ils
sont « skipped ». L'appel réel à Gemini se vérifie avec ``python -m app.llm_check ping simple``.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.llm import get_llm_provider
from app.auth.passwords import hash_password
from app.auth.tokens import create_access_token
from app.config import Settings, get_settings
from app.db.models import AuditLog, User
from app.db.session import get_session, session_scope
from app.llm.base import (
    LLMBadResponse,
    LLMBlocked,
    LLMRateLimited,
    LLMRejected,
    LLMResult,
    LLMTimeout,
    LLMUnavailable,
)
from app.main import create_app
from tests.pg_support import temporary_schema_engine

SECRET = "k" * 48
SECRET_TEXT = "phrase-confidentielle-du-test"


class FakeProvider:
    """Double de test : enregistre les appels et rend un résultat ou lève l'erreur donnée."""

    name = "gemini"

    def __init__(self, total_tokens=10, error=None):
        self.total_tokens = total_tokens
        self.error = error
        self.calls = []

    def generate(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return LLMResult(
            text="Réponse du double", model=kwargs["model"], finish_reason="STOP",
            prompt_tokens=4, output_tokens=6, total_tokens=self.total_tokens,
        )  # fmt: skip


@pytest.fixture(scope="module")
def engine():
    with temporary_schema_engine() as test_engine:
        yield test_engine


@pytest.fixture(scope="module")
def settings():
    return Settings(
        _env_file=None, jwt_secret_key=SECRET, gemini_api_key="x" * 20,
        llm_model_simple="modele-simple", llm_model_medium="modele-moyen",
        llm_daily_request_limit=3, llm_daily_token_limit=1000, llm_max_output_tokens=100,
    )  # fmt: skip


@pytest.fixture
def provider():
    return FakeProvider()


@pytest.fixture
def client(engine, settings, provider):
    app = create_app()

    def _session():
        with session_scope(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_llm_provider] = lambda: provider
    return TestClient(app)


def _user_headers(engine):
    with session_scope(engine) as session:
        user = User(email=f"{uuid.uuid4().hex[:10]}@exemple.cm", is_active=True, password_hash=hash_password("x" * 14))
        session.add(user)
    token, _ = create_access_token(user.id, secret=SECRET, expires_minutes=60)
    return user, {"Authorization": f"Bearer {token}"}


def _audit(engine, user) -> list[AuditLog]:
    with Session(engine) as session:
        rows = session.scalars(
            select(AuditLog).where(AuditLog.user_id == user.id, AuditLog.action == "llm_chat").order_by(AuditLog.id)
        )
        return list(rows)


def _chat(client, headers, text="Bonjour", **extra):
    return client.post("/llm/chat", json={"messages": [{"role": "user", "content": text}], **extra}, headers=headers)


def test_requires_authentication(client):
    assert _chat(client, {}).status_code == 401
    assert _chat(client, {"Authorization": "Bearer faux"}).status_code == 401


def test_success_returns_answer_and_writes_audit_without_content(client, engine, provider):
    user, headers = _user_headers(engine)

    response = _chat(client, headers, SECRET_TEXT, system="Contexte confidentiel")

    assert response.status_code == 200
    assert response.json() == {
        "text": "Réponse du double", "model": "modele-simple", "tier": "simple", "finish_reason": "STOP",
        "usage": {"prompt_tokens": 4, "output_tokens": 6, "total_tokens": 10},
    }  # fmt: skip
    assert provider.calls[0]["model"] == "modele-simple"
    (row,) = _audit(engine, user)
    assert (row.result, row.tool, row.permission_level, row.authorization_decision) == ("success", "gemini", 1, "allowed")
    assert row.details["usage"] == {"prompt": 4, "output": 6, "total": 10}
    assert row.details["model"] == "modele-simple" and row.details["tier"] == "simple"
    assert row.correlation_id
    dump = f"{row.details} {row.error} {row.decision_reason}"
    assert SECRET_TEXT not in dump and "Contexte confidentiel" not in dump and "Réponse du double" not in dump


def test_correlation_id_is_the_request_id(client, engine):
    user, headers = _user_headers(engine)
    _chat(client, {**headers, "X-Request-ID": "req-llm-1"})
    assert _audit(engine, user)[0].correlation_id == "req-llm-1"


def test_tier_selects_the_model_and_unconfigured_tier_is_503(client, engine, provider):
    user, headers = _user_headers(engine)
    assert _chat(client, headers, tier="medium").json()["model"] == "modele-moyen"
    assert _chat(client, headers, tier="hard").status_code == 503
    assert len(provider.calls) == 1  # aucun appel pour le niveau non configuré
    assert len(_audit(engine, user)) == 1


def test_unknown_tier_and_bad_payloads_are_422(client, engine, provider):
    _, headers = _user_headers(engine)
    assert _chat(client, headers, tier="geant").status_code == 422
    assert client.post("/llm/chat", json={"messages": []}, headers=headers).status_code == 422
    assert client.post("/llm/chat", json={"messages": [{"role": "system", "content": "x"}]}, headers=headers).status_code == 422
    assert client.post("/llm/chat", json={"messages": [{"role": "user", "content": ""}]}, headers=headers).status_code == 422
    assistant_last = {"messages": [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]}
    assert client.post("/llm/chat", json=assistant_last, headers=headers).status_code == 422
    assert _chat(client, headers, max_output_tokens=5).status_code == 422
    assert _chat(client, headers, temperature=3).status_code == 422
    assert provider.calls == []


def test_conversation_too_long_is_413(client, engine, provider):
    _, headers = _user_headers(engine)
    messages = [{"role": "user", "content": "a" * 8000}, {"role": "assistant", "content": "b" * 8000}] * 3
    messages.append({"role": "user", "content": "c" * 8000})
    response = client.post("/llm/chat", json={"messages": messages}, headers=headers)
    assert response.status_code == 413
    assert provider.calls == []


def test_output_tokens_are_capped_by_settings(client, engine, provider):
    _, headers = _user_headers(engine)
    _chat(client, headers, max_output_tokens=5000)
    _chat(client, headers, max_output_tokens=50)
    _chat(client, headers)
    assert [c["max_output_tokens"] for c in provider.calls] == [100, 50, 100]


def test_daily_request_limit(client, engine, provider):
    user, headers = _user_headers(engine)
    for _ in range(3):
        assert _chat(client, headers).status_code == 200

    response = _chat(client, headers)

    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert len(provider.calls) == 3  # le 4e appel n'a pas atteint le fournisseur
    last = _audit(engine, user)[-1]
    assert (last.result, last.authorization_decision, last.decision_reason) == ("denied", "denied", "daily_requests_limit")
    # un refus n'est pas compté : l'utilisateur reste bloqué mais le compteur ne grossit pas
    assert _chat(client, headers).status_code == 429
    other, other_headers = _user_headers(engine)
    assert _chat(client, other_headers).status_code == 200  # autre utilisateur : compteur séparé
    assert len(_audit(engine, other)) == 1


def test_daily_token_limit(client, engine, provider):
    user, headers = _user_headers(engine)
    provider.total_tokens = 600
    assert _chat(client, headers).status_code == 200
    assert _chat(client, headers).status_code == 200  # 600 < 1000 avant l'appel
    response = _chat(client, headers)  # 1200 >= 1000
    assert response.status_code == 429
    assert _audit(engine, user)[-1].decision_reason == "daily_tokens_limit"
    assert len(provider.calls) == 2


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (LLMRateLimited(12), 429, "llm_rate_limited"),
        (LLMBlocked("x"), 422, "llm_blocked"),
        (LLMTimeout("t"), 504, "llm_timeout"),
        (LLMUnavailable("u"), 503, "llm_unavailable"),
        (LLMRejected("INVALID_ARGUMENT"), 502, "llm_rejected"),
        (LLMBadResponse("b"), 502, "llm_bad_response"),
    ],
)
def test_provider_errors_are_mapped_and_audited(client, engine, provider, error, status, code):
    user, headers = _user_headers(engine)
    provider.error = error

    response = _chat(client, headers, SECRET_TEXT)

    assert response.status_code == status
    assert SECRET_TEXT not in response.text
    (row,) = _audit(engine, user)
    assert (row.result, row.error, row.authorization_decision) == ("failure", code, "allowed")
    assert SECRET_TEXT not in f"{row.details} {row.error}"
    if isinstance(error, LLMRateLimited):
        assert response.headers["Retry-After"] == "12"


def test_failed_calls_count_toward_the_daily_request_limit(client, engine, provider):
    _, headers = _user_headers(engine)
    provider.error = LLMUnavailable("u")
    for _ in range(3):
        assert _chat(client, headers).status_code == 503
    provider.error = None
    assert _chat(client, headers).status_code == 429


def test_missing_api_key_is_503_without_calling_anything(engine):
    no_key = Settings(_env_file=None, jwt_secret_key=SECRET, llm_model_simple="m")
    app = create_app()

    def _session():
        with session_scope(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_settings] = lambda: no_key
    _, headers = _user_headers(engine)

    response = TestClient(app).post(
        "/llm/chat", json={"messages": [{"role": "user", "content": "x"}]}, headers=headers
    )

    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]
