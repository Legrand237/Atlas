"""Tests de l'étape 2b sur une VRAIE base PostgreSQL (celle de DATABASE_URL, dans backend/.env).

Chaque exécution crée un schéma temporaire au nom aléatoire, y applique les migrations Alembic,
teste, puis supprime ce schéma. Le schéma ``public`` et tes données ne sont jamais touchés.
Sans DATABASE_URL, ces tests sont marqués « skipped » (ils ne comptent PAS comme réussis).

Connexion directe : le « pooler » de Neon (hôte contenant ``-pooler``) refuse l'option ``search_path``.
Ces tests utilisent donc toujours une connexion DIRECTE, choisie ainsi :
1. ``DATABASE_URL_DIRECT`` (variable d'environnement ou ligne de ``backend/.env``), si elle est définie ;
2. sinon ``DATABASE_URL`` dont le suffixe ``-pooler`` est retiré du nom d'hôte (hôtes ``*.neon.tech`` seulement) ;
3. sinon ``DATABASE_URL`` telle quelle (déjà directe).
Aucune adresse ni aucun mot de passe n'est affiché ou écrit par ces tests.
"""

import os
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pytest
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.audit import record_event
from app.db.models import AuditLog, Base, User
from app.db.session import build_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
DIRECT_URL_VARIABLE = "DATABASE_URL_DIRECT"


def to_direct_url(raw_url: str) -> str:
    """Retire ``-pooler`` du nom d'hôte d'une adresse Neon (``ep-xxx-pooler.region.neon.tech``).

    Neon documente la connexion poolée comme « nom d'hôte + ``-pooler`` » : la retirer donne la connexion
    directe. Toute autre adresse (hôte direct, autre fournisseur) est renvoyée inchangée.
    Seul le nom d'hôte est modifié : identifiants, port, base et options sont conservés.
    """
    parts = urlsplit(raw_url)
    userinfo, at, host_port = parts.netloc.rpartition("@")
    host, colon, port = host_port.partition(":")
    first_label, dot, rest = host.partition(".")
    if not (host.endswith(".neon.tech") and first_label.endswith("-pooler")):
        return raw_url
    direct_host = first_label[: -len("-pooler")] + dot + rest
    return urlunsplit(parts._replace(netloc=f"{userinfo}{at}{direct_host}{colon}{port}"))


def _direct_database_url() -> str | None:
    """Adresse DIRECTE de la base (au format SQLAlchemy/psycopg), ou None si rien n'est configuré."""
    configured = get_settings().database_url
    override = os.environ.get(DIRECT_URL_VARIABLE) or dotenv_values(BACKEND_DIR / ".env").get(DIRECT_URL_VARIABLE)
    if override:
        # Même validation et même conversion (postgresql:// -> postgresql+psycopg://) que DATABASE_URL.
        return Settings(_env_file=None, database_url=override.strip()).database_url.get_secret_value()
    if configured is None:
        return None
    return to_direct_url(configured.get_secret_value())


def test_pooler_host_is_converted_to_direct_host():
    pooled = "postgresql+psycopg://u:p%40ss@ep-cool-name-123456-pooler.eu-central-1.aws.neon.tech:5432/db?sslmode=require"
    direct = "postgresql+psycopg://u:p%40ss@ep-cool-name-123456.eu-central-1.aws.neon.tech:5432/db?sslmode=require"
    assert to_direct_url(pooled) == direct


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://u:p@ep-cool-name-123456.eu-central-1.aws.neon.tech/db",  # déjà directe
        "postgresql+psycopg://u:p@mon-pooler.exemple.com/db",  # autre fournisseur : on ne devine pas
        "postgresql+psycopg://u:p@localhost:5432/db",
    ],
)
def test_other_urls_are_left_unchanged(url):
    assert to_direct_url(url) == url


@pytest.fixture(scope="module")
def engine():
    """Moteur dont le search_path pointe vers un schéma temporaire, avec les migrations appliquées."""
    raw_url = _direct_database_url()
    if raw_url is None:
        pytest.skip("DATABASE_URL non configurée : test sur base réelle non exécuté")
    schema = f"test_atlas_{uuid.uuid4().hex[:12]}"
    admin = build_engine(raw_url, connect_timeout=30)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    test_engine = build_engine(raw_url, connect_timeout=30, options=f"-c search_path={schema}")
    try:
        # Garde-fou : on ne migre JAMAIS tant que la session n'est pas réellement dans le schéma temporaire.
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


def _migrate(engine, direction: str, revision: str) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.attributes["configure_logger"] = False  # ne pas toucher à la configuration des journaux de pytest
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        getattr(command, direction)(config, revision)


@pytest.fixture
def session(engine):
    """Session dont tout est annulé à la fin du test (rollback)."""
    with Session(engine) as db:
        yield db
        db.rollback()


def _user(db: Session, email: str | None = None) -> User:
    user = User(email=email or f"{uuid.uuid4().hex[:8]}@exemple.cm")
    db.add(user)
    db.flush()
    return user


def test_migration_creates_the_expected_tables(engine):
    assert {"users", "audit_logs", "alembic_version"} <= set(inspect(engine).get_table_names())


def test_columns_in_database_match_the_models(engine):
    inspector = inspect(engine)
    for name, table in Base.metadata.tables.items():
        in_database = {column["name"] for column in inspector.get_columns(name)}
        assert in_database == set(table.columns.keys()), name


def test_user_roundtrip_and_defaults(session):
    user = _user(session, "Awa@Exemple.CM")
    session.refresh(user)
    assert user.email == "awa@exemple.cm"
    assert user.is_active is True
    assert user.created_at is not None and user.id is not None


def test_duplicate_email_is_rejected(session):
    _user(session, "doublon@exemple.cm")
    with pytest.raises(IntegrityError):
        _user(session, "doublon@exemple.cm")


def test_database_rejects_uppercase_email_even_without_the_model(session):
    with pytest.raises(IntegrityError):
        session.execute(text("INSERT INTO users (email) VALUES ('MAJ@exemple.cm')"))


def test_record_event_writes_a_row_with_defaults(session):
    user = _user(session)
    entry = record_event(
        session,
        correlation_id="req-abc.1",
        actor_type="user",
        user_id=user.id,
        action="connexion",
        result="success",
        details={"methode": "mot_de_passe"},
    )
    session.refresh(entry)
    assert entry.id is not None and entry.occurred_at is not None
    assert entry.authorization_decision == "not_applicable"
    assert entry.details == {"methode": "mot_de_passe"}


def test_record_event_stores_authorization_decision_and_reason(session):
    entry = record_event(
        session,
        correlation_id="req-2",
        actor_type="agent",
        tool="calculatrice",
        action="calculer",
        permission_level=0,
        authorization_decision="denied",
        decision_reason="niveau non autorisé",
        result="denied",
        error="refusé par la politique",
    )
    session.refresh(entry)
    assert (entry.authorization_decision, entry.result, entry.permission_level) == ("denied", "denied", 0)


def test_database_rejects_invalid_audit_rows_even_without_the_service(session):
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO audit_logs (correlation_id, actor_type, action, result) "
                "VALUES ('r', 'system', 'x', 'peut-etre')"
            )
        )


def test_audit_rows_cannot_be_updated_deleted_or_truncated(session):
    entry = record_event(session, correlation_id="req-3", actor_type="system", action="x", result="success")
    for statement in (
        "UPDATE audit_logs SET result = 'failure'",
        "DELETE FROM audit_logs",
        "TRUNCATE audit_logs",
    ):
        with pytest.raises(DBAPIError) as info, session.begin_nested():
            session.execute(text(statement))
        assert "ajout seul" in str(info.value)
    assert session.get(AuditLog, entry.id) is not None


def test_user_with_audit_history_cannot_be_deleted(session):
    user = _user(session)
    record_event(session, correlation_id="req-4", actor_type="user", user_id=user.id, action="x", result="success")
    with pytest.raises(IntegrityError), session.begin_nested():
        session.execute(text("DELETE FROM users WHERE id = :id"), {"id": user.id})


def test_downgrade_then_upgrade_again(engine):
    # Ce test change la structure : il reste en dernier (pytest exécute les tests dans l'ordre du fichier).
    _migrate(engine, "downgrade", "base")
    assert "users" not in inspect(engine).get_table_names()
    _migrate(engine, "upgrade", "head")
    assert {"users", "audit_logs"} <= set(inspect(engine).get_table_names())
