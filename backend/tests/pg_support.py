"""Aide pour les tests sur la vraie base : un moteur dont le search_path pointe vers un schéma temporaire.

Réutilise la logique déjà vérifiée de ``test_db_migrations`` (adresse directe, migrations Alembic).
Le schéma ``public`` n'est jamais touché ; le schéma temporaire est supprimé à la fin.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from sqlalchemy import Engine, text

from app.db.session import build_engine
from tests.test_db_migrations import _direct_database_url, _migrate


@contextmanager
def temporary_schema_engine() -> Iterator[Engine]:
    """Crée un schéma aléatoire, y applique toutes les migrations, puis le supprime. Saute le test sans base."""
    raw_url = _direct_database_url()
    if raw_url is None:
        pytest.skip("DATABASE_URL non configurée : test sur base réelle non exécuté")
    schema = f"test_atlas_{uuid.uuid4().hex[:12]}"
    admin = build_engine(raw_url, connect_timeout=30)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    test_engine = build_engine(raw_url, connect_timeout=30, options=f"-c search_path={schema}")
    try:
        with test_engine.connect() as connection:
            current = connection.execute(text("SELECT current_schema()")).scalar_one()
        if current != schema:
            pytest.fail("search_path non appliqué : test arrêté avant toute migration (schéma public protégé)")
        _migrate(test_engine, "upgrade", "head")
        yield test_engine
    finally:
        test_engine.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
