"""Écriture dans le journal d'audit (règle 41.15). Ajout seul : il n'existe aucune fonction de modification.

Utilisation (le ``correlation_id`` est celui de la requête HTTP, ``request.state.request_id``) :

    with session_scope() as session:
        record_event(session, correlation_id=rid, actor_type="user", user_id=uid,
                     action="login", result="success")

``record_event`` n'enregistre rien définitivement : la validation (commit) revient à l'appelant,
ce qui permet d'écrire l'audit dans la même transaction que l'action tracée.
"""

import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.request_id import is_valid_request_id
from app.db.models import ACTOR_TYPES, AUDIT_RESULTS, AUTHORIZATION_DECISIONS, AuditLog

MAX_TEXT_LENGTH = 2000
_SENSITIVE_KEY = re.compile(r"password|passwd|secret|token|api[_-]?key|authorization|credential", re.IGNORECASE)


class AuditError(ValueError):
    """Événement d'audit invalide : il n'est pas enregistré."""


def _check_choice(name: str, value: str, allowed: tuple[str, ...]) -> None:
    if value not in allowed:
        raise AuditError(f"{name} invalide ({value!r}) : attendu {', '.join(allowed)}.")


def _find_sensitive_key(value: Any) -> str | None:
    """Cherche récursivement une clé suspecte (mot de passe, token...) dans ``details``."""
    if isinstance(value, dict):
        for key, inner in value.items():
            if _SENSITIVE_KEY.search(str(key)):
                return str(key)
            found = _find_sensitive_key(inner)
            if found is not None:
                return found
    elif isinstance(value, (list, tuple)):
        for inner in value:
            found = _find_sensitive_key(inner)
            if found is not None:
                return found
    return None


def validate_event(
    *,
    correlation_id: str,
    actor_type: str,
    action: str,
    result: str,
    user_id: uuid.UUID | None = None,
    permission_level: int | None = None,
    authorization_decision: str = "not_applicable",
    details: dict[str, Any] | None = None,
) -> None:
    """Vérifie un événement avant écriture ; lève ``AuditError`` s'il est invalide.

    Les mêmes règles sont aussi imposées par la base (contraintes CHECK) : cette vérification
    donne un message clair avant d'atteindre la base.
    """
    if not is_valid_request_id(correlation_id):
        raise AuditError("correlation_id invalide (1 à 64 caractères : lettres, chiffres, . _ -).")
    _check_choice("actor_type", actor_type, ACTOR_TYPES)
    _check_choice("result", result, AUDIT_RESULTS)
    _check_choice("authorization_decision", authorization_decision, AUTHORIZATION_DECISIONS)
    if actor_type == "user" and user_id is None:
        raise AuditError("user_id est obligatoire quand actor_type vaut 'user'.")
    if not action or len(action) > 100:
        raise AuditError("action est obligatoire (100 caractères au maximum).")
    if permission_level is not None and not 0 <= permission_level <= 5:
        raise AuditError("permission_level doit être compris entre 0 et 5.")
    if details is not None:
        if not isinstance(details, dict):
            raise AuditError("details doit être un dictionnaire.")
        suspicious = _find_sensitive_key(details)
        if suspicious is not None:
            raise AuditError(f"details contient une clé sensible ({suspicious!r}) : un secret ne s'écrit jamais dans l'audit.")


def record_event(
    session: Session,
    *,
    correlation_id: str,
    actor_type: str,
    action: str,
    result: str,
    user_id: uuid.UUID | None = None,
    task_id: str | None = None,
    tool: str | None = None,
    permission_level: int | None = None,
    authorization_decision: str = "not_applicable",
    decision_reason: str | None = None,
    error: str | None = None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Ajoute une ligne au journal d'audit dans la transaction de ``session`` (sans commit)."""
    validate_event(
        correlation_id=correlation_id,
        actor_type=actor_type,
        action=action,
        result=result,
        user_id=user_id,
        permission_level=permission_level,
        authorization_decision=authorization_decision,
        details=details,
    )
    entry = AuditLog(
        correlation_id=correlation_id,
        actor_type=actor_type,
        user_id=user_id,
        task_id=task_id,
        tool=tool,
        action=action,
        permission_level=permission_level,
        authorization_decision=authorization_decision,
        decision_reason=decision_reason[:MAX_TEXT_LENGTH] if decision_reason else None,
        result=result,
        error=error[:MAX_TEXT_LENGTH] if error else None,
        details=details if details is not None else {},
    )
    session.add(entry)
    session.flush()  # envoie l'INSERT : une erreur de la base apparaît tout de suite, et ``id`` est connu
    return entry
