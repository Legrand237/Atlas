"""Accès à la base de données PostgreSQL (SQLAlchemy) : moteur, vérification, sessions.

Les messages d'erreur ne contiennent jamais l'adresse complète ni le mot de passe.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings


class DatabaseNotConfigured(RuntimeError):
    """DATABASE_URL est absente ou vide."""


class DatabaseUnavailable(RuntimeError):
    """La base est configurée mais la connexion ou la requête a échoué."""


def build_engine(url: str, *, connect_timeout: int = 10, options: str | None = None) -> Engine:
    """Crée un moteur SQLAlchemy. ``pool_pre_ping`` teste une connexion avant de la réutiliser
    (utile avec Neon, qui met la base en veille après quelques minutes).

    ``options`` : options PostgreSQL envoyées à la connexion (ex. ``-c search_path=mon_schema``,
    utilisé par les tests). Refusées par les connexions « pooler » de Neon : utiliser la connexion directe.
    """
    connect_args: dict[str, object] = {}
    if url.startswith("postgresql"):
        connect_args["connect_timeout"] = connect_timeout
        if options:
            connect_args["options"] = options
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


@lru_cache
def get_engine() -> Engine:
    """Moteur de l'application, créé au premier usage."""
    url = get_settings().database_url
    if url is None:
        raise DatabaseNotConfigured("DATABASE_URL n'est pas définie (voir backend/.env.example).")
    return build_engine(url.get_secret_value())


def check_connection(engine: Engine) -> str:
    """Exécute une vraie requête ``SELECT 1`` et retourne la version du serveur.

    Lève ``DatabaseUnavailable`` (message sans secret) si la base ne répond pas.
    """
    try:
        with engine.connect() as connection:
            if connection.execute(text("SELECT 1")).scalar_one() != 1:
                raise DatabaseUnavailable("Réponse inattendue de la base.")
            if engine.dialect.name == "postgresql":
                return str(connection.execute(text("SHOW server_version")).scalar_one())
            return f"{engine.dialect.name} (test local)"
    except SQLAlchemyError as exc:
        # On n'inclut pas str(exc) : il peut contenir l'adresse de connexion.
        raise DatabaseUnavailable(
            f"Connexion impossible ({type(exc).__name__}). Vérifie DATABASE_URL, "
            "le réseau et l'état du projet Neon."
        ) from None


@contextmanager
def session_scope(engine: Engine | None = None) -> Iterator[Session]:
    """Ouvre une session : validation (commit) à la sortie normale, annulation (rollback) en cas d'erreur."""
    session = Session(engine or get_engine(), expire_on_commit=False)
    try:
        yield session
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """Dépendance FastAPI : une session par requête (commit si tout va bien, rollback sinon)."""
    with session_scope() as session:
        yield session
