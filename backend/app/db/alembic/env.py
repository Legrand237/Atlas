"""Environnement Alembic : relie les migrations à la base configurée dans DATABASE_URL."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection

from app.db.models import Base
from app.db.session import get_engine

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Applique les migrations sur la base réelle.

    Les tests peuvent fournir leur propre connexion via ``config.attributes["connection"]``.
    """
    provided = config.attributes.get("connection")
    if provided is not None:
        _run(provided)
        return
    with get_engine().connect() as connection:
        _run(connection)


if context.is_offline_mode():
    raise RuntimeError("Le mode hors ligne (--sql) n'est pas pris en charge : utilise `alembic upgrade head`.")

run_migrations_online()
