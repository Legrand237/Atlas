"""Modèles SQLAlchemy (étape 2b) : ``users`` et ``audit_logs``.

La structure réelle de la base est créée par la migration Alembic ``0001`` (SQL écrit à la main) ;
ces modèles doivent rester identiques : un test compare les colonnes des deux.
Les autres tables du modèle de données (conversations, tasks, ...) arrivent avec leurs étapes.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    MetaData,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, validates

# Noms de contraintes prévisibles (utile pour les migrations et les messages d'erreur).
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

ACTOR_TYPES = ("user", "agent", "system")
AUTHORIZATION_DECISIONS = ("allowed", "denied", "confirmation_required", "not_applicable")
AUDIT_RESULTS = ("success", "failure", "denied")


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class User(Base):
    """Compte utilisateur. ``password_hash`` est vide (NULL) tant qu'aucun mot de passe n'est défini : connexion impossible."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email"),
        CheckConstraint("email = lower(email) AND position('@' in email) > 1", name="email_format"),
        CheckConstraint("password_hash IS NULL OR length(password_hash) > 0", name="password_hash_not_empty"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(String(320))
    display_name: Mapped[str | None] = mapped_column(String(100))
    password_hash: Mapped[str | None] = mapped_column(Text)  # empreinte argon2 (migration 0002) ; jamais le mot de passe
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @validates("email")
    def _normalize_email(self, _key: str, value: str) -> str:
        """Adresse e-mail en minuscules, sans espaces autour ; refuse une adresse sans « @ »."""
        email = value.strip().lower()
        if email.find("@") < 1:
            raise ValueError("Adresse e-mail invalide.")
        return email


class AuditLog(Base):
    """Journal d'audit en ajout seul (règle 41.15).

    La base interdit UPDATE, DELETE et TRUNCATE sur cette table (déclencheurs créés par la migration).
    ``task_id`` n'a pas de clé étrangère : la table ``tasks`` n'existe pas encore.
    ``details`` ne doit contenir aucun secret (le service ``record_event`` refuse les clés suspectes).
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint("actor_type IN ('user', 'agent', 'system')", name="actor_type"),
        CheckConstraint(
            "authorization_decision IN ('allowed', 'denied', 'confirmation_required', 'not_applicable')",
            name="authorization_decision",
        ),
        CheckConstraint("result IN ('success', 'failure', 'denied')", name="result"),
        CheckConstraint(
            "permission_level IS NULL OR permission_level BETWEEN 0 AND 5", name="permission_level"
        ),
        CheckConstraint("actor_type <> 'user' OR user_id IS NOT NULL", name="user_actor_has_user_id"),
        CheckConstraint("length(correlation_id) > 0", name="correlation_id_not_empty"),
        Index("ix_audit_logs_correlation_id", "correlation_id"),
        Index("ix_audit_logs_occurred_at", "occurred_at"),
        Index("ix_audit_logs_user_id_occurred_at", "user_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    correlation_id: Mapped[str] = mapped_column(String(64))
    actor_type: Mapped[str] = mapped_column(String(16))
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"))
    task_id: Mapped[str | None] = mapped_column(String(64))
    tool: Mapped[str | None] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    permission_level: Mapped[int | None] = mapped_column(SmallInteger)
    authorization_decision: Mapped[str] = mapped_column(
        String(24), server_default=text("'not_applicable'")
    )
    decision_reason: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str] = mapped_column(String(16))
    error: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
