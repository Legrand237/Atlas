"""Service d'authentification : connexion avec limitation des essais, création de compte, audit.

Chaque tentative de connexion est écrite dans ``audit_logs`` (action ``login``) avec l'identifiant de
corrélation de la requête. Ni mot de passe ni adresse e-mail n'y sont écrits.
Les erreurs ne distinguent jamais « compte inconnu » de « mauvais mot de passe » vers l'extérieur.
"""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.passwords import dummy_hash, hash_password, needs_rehash, verify_password
from app.db.audit import record_event
from app.db.models import AuditLog, User


class AuthenticationFailed(Exception):
    """Identifiants invalides (message volontairement vague)."""


class TooManyAttempts(Exception):
    """Trop d'échecs récents pour ce compte."""


class UserAlreadyExists(Exception):
    """Un compte existe déjà avec cette adresse e-mail."""


def _recent_failures(session: Session, user_id: uuid.UUID, *, window_minutes: int) -> int:
    """Nombre d'échecs de connexion dans la fenêtre, en ne comptant que ceux postérieurs à la dernière réussite."""
    since = datetime.now(UTC) - timedelta(minutes=window_minutes)
    last_success = session.scalar(
        select(func.max(AuditLog.occurred_at)).where(
            AuditLog.user_id == user_id, AuditLog.action == "login", AuditLog.result == "success"
        )
    )
    if last_success is not None and last_success > since:
        since = last_success
    return session.scalar(
        select(func.count())
        .select_from(AuditLog)
        .where(
            AuditLog.user_id == user_id,
            AuditLog.action == "login",
            AuditLog.result == "failure",
            AuditLog.occurred_at > since,
        )
    ) or 0


def authenticate(
    session: Session,
    *,
    email: str,
    password: str,
    correlation_id: str,
    max_failures: int,
    window_minutes: int,
) -> User:
    """Vérifie les identifiants ; retourne l'utilisateur ou lève ``AuthenticationFailed`` / ``TooManyAttempts``.

    L'audit est validé (commit) ici même avant de lever une erreur, pour que les échecs soient bien conservés.
    """
    user = session.scalar(select(User).where(User.email == email.strip().lower()))

    if user is None:
        verify_password(password, dummy_hash())  # même durée qu'un vrai refus
        record_event(
            session, correlation_id=correlation_id, actor_type="system", action="login",
            result="failure", details={"reason": "unknown_account"},
        )  # fmt: skip
        session.commit()
        raise AuthenticationFailed

    if not user.is_active or not user.password_hash:
        verify_password(password, dummy_hash())
        record_event(
            session, correlation_id=correlation_id, actor_type="user", user_id=user.id, action="login",
            result="failure", details={"reason": "inactive_or_no_password"},
        )  # fmt: skip
        session.commit()
        raise AuthenticationFailed

    if _recent_failures(session, user.id, window_minutes=window_minutes) >= max_failures:
        record_event(
            session, correlation_id=correlation_id, actor_type="user", user_id=user.id, action="login",
            result="denied", authorization_decision="denied",
            decision_reason="trop d'échecs de connexion récents",
        )  # fmt: skip
        session.commit()
        raise TooManyAttempts

    if not verify_password(password, user.password_hash):
        record_event(
            session, correlation_id=correlation_id, actor_type="user", user_id=user.id, action="login",
            result="failure", details={"reason": "wrong_password"},
        )  # fmt: skip
        session.commit()
        raise AuthenticationFailed

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    record_event(
        session, correlation_id=correlation_id, actor_type="user", user_id=user.id, action="login",
        result="success", authorization_decision="allowed", decision_reason="mot de passe valide",
    )  # fmt: skip
    session.commit()
    return user


def create_user(
    session: Session, *, email: str, password: str, display_name: str | None = None, correlation_id: str | None = None
) -> User:
    """Crée un compte (utilisé par la commande ``python -m app.manage create-user``).

    Lève ``WeakPassword`` (mot de passe trop faible), ``ValueError`` (e-mail invalide) ou ``UserAlreadyExists``.
    L'inscription n'est PAS exposée par l'API : un agent personnel ne doit pas accepter d'inconnus.
    """
    password_hash = hash_password(password)  # valide aussi la force du mot de passe
    user = User(email=email, display_name=display_name, password_hash=password_hash)
    try:
        with session.begin_nested():
            session.add(user)
            session.flush()
    except IntegrityError:
        raise UserAlreadyExists from None
    record_event(
        session, correlation_id=correlation_id or uuid.uuid4().hex, actor_type="system", user_id=user.id,
        action="user_create", result="success", details={"via": "manage"},
    )  # fmt: skip
    session.commit()
    return user
