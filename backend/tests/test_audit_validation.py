"""Tests de l'étape 2b qui n'ont pas besoin de base de données :
modèles, validation des événements d'audit, cohérence des migrations."""

import uuid
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.db.audit import AuditError, validate_event
from app.db.models import AuditLog, Base, User

BACKEND_DIR = Path(__file__).resolve().parents[1]
VALID = {"correlation_id": "req-123", "actor_type": "system", "action": "demarrage", "result": "success"}


def test_metadata_declares_users_and_audit_logs():
    assert set(Base.metadata.tables) == {"users", "audit_logs"}


def test_audit_logs_has_the_fields_required_by_rule_41_15():
    columns = set(Base.metadata.tables["audit_logs"].columns.keys())
    required = {
        "occurred_at", "correlation_id", "actor_type", "user_id", "task_id", "tool", "action",
        "permission_level", "authorization_decision", "decision_reason", "result", "error",
    }  # fmt: skip
    assert required <= columns


def test_user_email_is_normalized():
    assert User(email="  Jean.Dupont@Exemple.CM ").email == "jean.dupont@exemple.cm"


@pytest.mark.parametrize("bad", ["", "sans-arobase", "@debut.cm"])
def test_user_email_without_valid_at_sign_is_rejected(bad):
    with pytest.raises(ValueError):
        User(email=bad)


def test_valid_event_is_accepted():
    validate_event(**VALID)


def test_valid_user_event_with_all_fields_is_accepted():
    validate_event(
        **{**VALID, "actor_type": "user"},
        user_id=uuid.uuid4(),
        permission_level=3,
        authorization_decision="confirmation_required",
        details={"fichier": "rapport.pdf", "taille": [1, 2]},
    )


@pytest.mark.parametrize(
    "change",
    [
        {"correlation_id": ""},
        {"correlation_id": "a b"},
        {"correlation_id": "x" * 65},
        {"actor_type": "robot"},
        {"result": "peut-etre"},
        {"authorization_decision": "peut-etre"},
        {"actor_type": "user"},  # user_id manquant
        {"action": ""},
        {"action": "a" * 101},
        {"permission_level": 6},
        {"permission_level": -1},
        {"details": ["pas", "un", "dict"]},
    ],
)
def test_invalid_event_is_rejected(change):
    with pytest.raises(AuditError):
        validate_event(**{**VALID, **change})


@pytest.mark.parametrize(
    "details",
    [{"password": "x"}, {"api_key": "x"}, {"Authorization": "Bearer x"}, {"a": {"b": [{"token": "x"}]}}],
)
def test_sensitive_keys_in_details_are_rejected(details):
    with pytest.raises(AuditError):
        validate_event(**VALID, details=details)


def test_audit_log_model_matches_the_table_name():
    assert AuditLog.__tablename__ == "audit_logs"


def test_migrations_have_a_single_head():
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    assert ScriptDirectory.from_config(config).get_heads() == ["0002"]
