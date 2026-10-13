"""Couche base de données : session, modèles, migrations (Alembic).

Les noms de ``session`` sont ré-exportés ici pour que ``from app.db import get_engine`` fonctionne.
Les modèles se importent explicitement : ``from app.db.models import User, AuditLog``.
"""

from app.db.session import (
    DatabaseNotConfigured,
    DatabaseUnavailable,
    build_engine,
    check_connection,
    get_engine,
    session_scope,
)

__all__ = [
    "DatabaseNotConfigured",
    "DatabaseUnavailable",
    "build_engine",
    "check_connection",
    "get_engine",
    "session_scope",
]
