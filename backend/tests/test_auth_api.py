"""Tests de l'authentification sur une VRAIE base PostgreSQL (schéma temporaire, voir pg_support.py).

Sans DATABASE_URL, ces tests sont marqués « skipped » (ils ne comptent PAS comme réussis).
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.auth.passwords import WeakPassword, hash_password, verify_password
from app.auth.service import UserAlreadyExists, create_user
from app.auth.tokens import create_access_token
from app.config import Settings, get_settings
from app.db.models import AuditLog, User
from app.db.session import get_session, session_scope
from app.main import create_app
from tests.pg_support import temporary_schema_engine

SECRET = "k" * 48
PASSWORD = "correct horse battery staple"


@pytest.fixture(scope="module")
def engine():
    with temporary_schema_engine() as test_engine:
        yield test_engine


@pytest.fixture(scope="module")
def settings():
    return Settings(_env_file=None, jwt_secret_key=SECRET, login_max_failures=3, login_window_minutes=15)


@pytest.fixture
def client(engine, settings):
    app = create_app()

    def _session():
        with session_scope(engine) as session:
            yield session

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def _new_user(engine, *, active=True, password=PASSWORD) -> User:
    email = f"{uuid.uuid4().hex[:10]}@exemple.cm"
    with session_scope(engine) as session:
        user = User(
            email=email,
            display_name="Awa",
            is_active=active,
            password_hash=hash_password(password) if password else None,
        )
        session.add(user)
    return user


def _audit(engine, **filters) -> list[AuditLog]:
    with Session(engine) as session:
        return list(session.scalars(select(AuditLog).filter_by(**filters).order_by(AuditLog.id)))


def _login(client, email, password, **headers):
    return client.post("/auth/login", json={"email": email, "password": password}, headers=headers)


def test_login_returns_a_token_that_opens_me(client, engine):
    user = _new_user(engine)

    response = _login(client, user.email, PASSWORD)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json() == {"id": str(user.id), "email": user.email, "display_name": "Awa"}
    assert "password" not in me.text and "argon2" not in me.text


def test_email_is_case_insensitive(client, engine):
    user = _new_user(engine)
    assert _login(client, user.email.upper(), PASSWORD).status_code == 200


def test_wrong_password_and_unknown_email_give_the_same_answer(client, engine):
    user = _new_user(engine)
    wrong = _login(client, user.email, "mauvais mot de passe")
    unknown = _login(client, "inconnu@exemple.cm", PASSWORD)
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "Identifiants invalides."}


def test_inactive_user_and_user_without_password_cannot_login(client, engine):
    inactive = _new_user(engine, active=False)
    no_password = _new_user(engine, password=None)
    assert _login(client, inactive.email, PASSWORD).status_code == 401
    assert _login(client, no_password.email, PASSWORD).status_code == 401


def test_every_attempt_is_audited_with_the_request_id_and_no_secret(client, engine):
    user = _new_user(engine)
    _login(client, user.email, "mauvais mot de passe", **{"X-Request-ID": "audit-fail-1"})
    _login(client, user.email, PASSWORD, **{"X-Request-ID": "audit-ok-1"})

    failure = _audit(engine, correlation_id="audit-fail-1")[0]
    success = _audit(engine, correlation_id="audit-ok-1")[0]
    assert (failure.action, failure.result, failure.user_id) == ("login", "failure", user.id)
    assert (success.action, success.result, success.authorization_decision) == ("login", "success", "allowed")
    dumped = str([(row.details, row.decision_reason, row.error) for row in (failure, success)])
    assert PASSWORD not in dumped and "mauvais" not in dumped and user.email not in dumped


def test_unknown_account_attempt_is_audited_as_system(client, engine):
    _login(client, "personne@exemple.cm", PASSWORD, **{"X-Request-ID": "audit-unknown-1"})
    row = _audit(engine, correlation_id="audit-unknown-1")[0]
    assert (row.actor_type, row.result, row.user_id) == ("system", "failure", None)


def test_account_is_locked_after_too_many_failures(client, engine):
    user = _new_user(engine)
    for _ in range(3):
        assert _login(client, user.email, "mauvais mot de passe").status_code == 401

    locked = _login(client, user.email, PASSWORD, **{"X-Request-ID": "audit-locked-1"})

    assert locked.status_code == 429
    assert locked.headers["retry-after"] == str(15 * 60)
    row = _audit(engine, correlation_id="audit-locked-1")[0]
    assert (row.result, row.authorization_decision) == ("denied", "denied")


def test_a_success_resets_the_failure_count(client, engine):
    user = _new_user(engine)
    for _ in range(2):
        _login(client, user.email, "mauvais mot de passe")
    assert _login(client, user.email, PASSWORD).status_code == 200
    for _ in range(2):
        assert _login(client, user.email, "mauvais mot de passe").status_code == 401
    assert _login(client, user.email, PASSWORD).status_code == 200


def test_login_without_jwt_secret_answers_503():
    app = create_app()
    app.dependency_overrides[get_session] = lambda: None  # la base n'est pas utilisée : 503 avant tout accès
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, jwt_secret_key=None)

    response = TestClient(app).post("/auth/login", json={"email": "a@b.cm", "password": PASSWORD})

    assert response.status_code == 503


def test_me_requires_a_valid_token(client, engine, settings):
    user = _new_user(engine)
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer nimportequoi"}).status_code == 401
    expired, _ = create_access_token(
        user.id, secret=SECRET, expires_minutes=1, now=datetime.now(UTC) - timedelta(hours=2)
    )
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    other_key, _ = create_access_token(user.id, secret="z" * 48, expires_minutes=30)
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {other_key}"}).status_code == 401
    unknown_user, _ = create_access_token(uuid.uuid4(), secret=SECRET, expires_minutes=30)
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {unknown_user}"}).status_code == 401


def test_token_stops_working_when_the_account_is_deactivated(client, engine, settings):
    user = _new_user(engine)
    token = _login(client, user.email, PASSWORD).json()["access_token"]
    with session_scope(engine) as session:
        session.execute(text("UPDATE users SET is_active = false WHERE id = :id"), {"id": user.id})
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_create_user_stores_a_hash_and_audits(engine):
    with session_scope(engine) as session:
        user = create_user(session, email="  Nouveau@Exemple.CM ", password=PASSWORD, display_name="Nouveau")
        user_id = user.id
    with Session(engine) as session:
        stored = session.get(User, user_id)
        assert stored.email == "nouveau@exemple.cm"
        assert stored.password_hash != PASSWORD and verify_password(PASSWORD, stored.password_hash)
    assert [row.action for row in _audit(engine, user_id=user_id)] == ["user_create"]


def test_create_user_rejects_duplicates_weak_passwords_and_bad_emails(engine):
    with session_scope(engine) as session:
        create_user(session, email="unique@exemple.cm", password=PASSWORD)
    with session_scope(engine) as session, pytest.raises(UserAlreadyExists):
        create_user(session, email="UNIQUE@exemple.cm", password=PASSWORD)
    with session_scope(engine) as session, pytest.raises(WeakPassword):
        create_user(session, email="faible@exemple.cm", password="court")
    with session_scope(engine) as session, pytest.raises(ValueError):
        create_user(session, email="pas-un-email", password=PASSWORD)
