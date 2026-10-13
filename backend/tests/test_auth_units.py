"""Tests de l'authentification qui n'ont pas besoin de base de données :
mots de passe, tokens, configuration, réponses 503."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.auth.passwords import (
    WeakPassword,
    dummy_hash,
    hash_password,
    needs_rehash,
    validate_password_strength,
    verify_password,
)
from app.auth.tokens import (
    ALGORITHM,
    TokenError,
    create_access_token,
    decode_access_token,
)
from app.config import Settings
from app.db.session import DatabaseNotConfigured, DatabaseUnavailable
from app.main import create_app

SECRET = "s" * 40
GOOD_PASSWORD = "un mot de passe assez long"


def test_hash_is_not_the_password_and_verifies():
    password_hash = hash_password(GOOD_PASSWORD)
    assert GOOD_PASSWORD not in password_hash
    assert password_hash.startswith("$argon2")
    assert verify_password(GOOD_PASSWORD, password_hash) is True


def test_wrong_password_does_not_verify():
    assert verify_password("un autre mot de passe", hash_password(GOOD_PASSWORD)) is False


def test_same_password_gives_different_hashes():
    assert hash_password(GOOD_PASSWORD) != hash_password(GOOD_PASSWORD)


@pytest.mark.parametrize("bad_hash", ["", "pas-une-empreinte", "$argon2id$v=19$m=1,t=1,p=1$xx$yy"])
def test_invalid_hash_never_raises_and_never_verifies(bad_hash):
    assert verify_password(GOOD_PASSWORD, bad_hash) is False


@pytest.mark.parametrize("weak", ["", "court", "onze chars!", " " * 20, "x" * 129])
def test_weak_passwords_are_rejected(weak):
    with pytest.raises(WeakPassword):
        validate_password_strength(weak)
    with pytest.raises(WeakPassword):
        hash_password(weak)


def test_fresh_hash_does_not_need_rehash():
    assert needs_rehash(hash_password(GOOD_PASSWORD)) is False


def test_dummy_hash_is_a_valid_hash_that_matches_no_real_password():
    assert dummy_hash().startswith("$argon2")
    assert verify_password(GOOD_PASSWORD, dummy_hash()) is False


def test_token_roundtrip():
    user_id = uuid.uuid4()
    token, expires_at = create_access_token(user_id, secret=SECRET, expires_minutes=30)
    assert decode_access_token(token, secret=SECRET) == user_id
    assert expires_at > datetime.now(UTC)


def test_expired_token_is_rejected():
    long_ago = datetime.now(UTC) - timedelta(hours=2)
    token, _ = create_access_token(uuid.uuid4(), secret=SECRET, expires_minutes=1, now=long_ago)
    with pytest.raises(TokenError):
        decode_access_token(token, secret=SECRET)


def test_token_signed_with_another_key_is_rejected():
    token, _ = create_access_token(uuid.uuid4(), secret="a" * 40, expires_minutes=30)
    with pytest.raises(TokenError):
        decode_access_token(token, secret="b" * 40)


def test_tampered_token_is_rejected():
    token, _ = create_access_token(uuid.uuid4(), secret=SECRET, expires_minutes=30)
    header, payload, signature = token.split(".")
    flipped = ("A" if signature[0] != "A" else "B") + signature[1:]
    with pytest.raises(TokenError):
        decode_access_token(f"{header}.{payload}.{flipped}", secret=SECRET)


@pytest.mark.parametrize("garbage", ["", "abc", "a.b.c", "x" * 500])
def test_garbage_is_rejected(garbage):
    with pytest.raises(TokenError):
        decode_access_token(garbage, secret=SECRET)


def test_unsigned_token_is_rejected():
    now = datetime.now(UTC)
    payload = {"sub": str(uuid.uuid4()), "iss": "atlas", "iat": now, "exp": now + timedelta(minutes=5)}
    unsigned = jwt.encode(payload, key=None, algorithm="none")
    with pytest.raises(TokenError):
        decode_access_token(unsigned, secret=SECRET)


def test_token_with_wrong_issuer_or_missing_claims_is_rejected():
    now = datetime.now(UTC)
    base = {"sub": str(uuid.uuid4()), "iat": now, "exp": now + timedelta(minutes=5)}
    for payload in ({**base, "iss": "autre"}, {k: v for k, v in base.items() if k != "sub"} | {"iss": "atlas"}):
        with pytest.raises(TokenError):
            decode_access_token(jwt.encode(payload, SECRET, algorithm=ALGORITHM), secret=SECRET)


def test_token_with_non_uuid_subject_is_rejected():
    now = datetime.now(UTC)
    payload = {"sub": "pas-un-uuid", "iss": "atlas", "iat": now, "exp": now + timedelta(minutes=5)}
    with pytest.raises(TokenError):
        decode_access_token(jwt.encode(payload, SECRET, algorithm=ALGORITHM), secret=SECRET)


def test_jwt_secret_key_defaults_to_none_and_empty_means_none(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    assert Settings(_env_file=None).jwt_secret_key is None
    monkeypatch.setenv("JWT_SECRET_KEY", "   ")
    assert Settings(_env_file=None).jwt_secret_key is None


def test_short_jwt_secret_key_is_rejected(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "trop-court")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_jwt_secret_key_is_hidden_in_repr():
    assert SECRET not in repr(Settings(_env_file=None, jwt_secret_key=SECRET))


@pytest.mark.parametrize(
    "field,value",
    [("session_duration_minutes", 1), ("session_duration_minutes", 5000), ("login_max_failures", 0), ("login_window_minutes", 0)],
)
def test_auth_limits_are_validated(field, value):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: value})


@pytest.mark.parametrize("error", [DatabaseNotConfigured("x"), DatabaseUnavailable("x")])
def test_database_errors_become_503_without_details(error):
    app = create_app()

    @app.get("/_boom")
    def boom():
        raise error

    response = TestClient(app, raise_server_exceptions=False).get("/_boom")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_unavailable"
    assert response.json()["error"]["message"] == "Base de données indisponible."
    assert response.headers["x-request-id"] == response.json()["error"]["request_id"]
