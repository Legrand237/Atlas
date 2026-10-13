"""Tables users et audit_logs (audit en ajout seul).

Revision ID: 0001
Revises:
Create Date: 2026-10-06

Le SQL est écrit à la main (et non généré) pour que la structure soit explicite et vérifiable.
Il doit rester identique aux modèles de ``app/db/models.py`` (un test compare les colonnes).
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

CREATE_USERS = """
CREATE TABLE users (
    id uuid NOT NULL DEFAULT gen_random_uuid(),
    email varchar(320) NOT NULL,
    display_name varchar(100),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT pk_users PRIMARY KEY (id),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT ck_users_email_format CHECK (email = lower(email) AND position('@' in email) > 1)
)
"""

CREATE_AUDIT_LOGS = """
CREATE TABLE audit_logs (
    id bigint GENERATED ALWAYS AS IDENTITY,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    correlation_id varchar(64) NOT NULL,
    actor_type varchar(16) NOT NULL,
    user_id uuid,
    task_id varchar(64),
    tool varchar(100),
    action varchar(100) NOT NULL,
    permission_level smallint,
    authorization_decision varchar(24) NOT NULL DEFAULT 'not_applicable',
    decision_reason text,
    result varchar(16) NOT NULL,
    error text,
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT pk_audit_logs PRIMARY KEY (id),
    CONSTRAINT fk_audit_logs_user_id_users FOREIGN KEY (user_id) REFERENCES users (id),
    CONSTRAINT ck_audit_logs_actor_type CHECK (actor_type IN ('user', 'agent', 'system')),
    CONSTRAINT ck_audit_logs_authorization_decision CHECK (
        authorization_decision IN ('allowed', 'denied', 'confirmation_required', 'not_applicable')
    ),
    CONSTRAINT ck_audit_logs_result CHECK (result IN ('success', 'failure', 'denied')),
    CONSTRAINT ck_audit_logs_permission_level CHECK (permission_level IS NULL OR permission_level BETWEEN 0 AND 5),
    CONSTRAINT ck_audit_logs_user_actor_has_user_id CHECK (actor_type <> 'user' OR user_id IS NOT NULL),
    CONSTRAINT ck_audit_logs_correlation_id_not_empty CHECK (length(correlation_id) > 0)
)
"""

CREATE_AUDIT_INDEXES = (
    "CREATE INDEX ix_audit_logs_correlation_id ON audit_logs (correlation_id)",
    "CREATE INDEX ix_audit_logs_occurred_at ON audit_logs (occurred_at)",
    "CREATE INDEX ix_audit_logs_user_id_occurred_at ON audit_logs (user_id, occurred_at)",
)

# Ajout seul : la base elle-même refuse de modifier, supprimer ou vider les lignes d'audit.
CREATE_APPEND_ONLY_FUNCTION = """
CREATE FUNCTION audit_logs_forbid_modification() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs est en ajout seul : % interdit', TG_OP
        USING ERRCODE = 'restrict_violation';
END;
$$
"""

CREATE_APPEND_ONLY_TRIGGERS = (
    """
    CREATE TRIGGER audit_logs_no_update_delete
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION audit_logs_forbid_modification()
    """,
    """
    CREATE TRIGGER audit_logs_no_truncate
    BEFORE TRUNCATE ON audit_logs
    FOR EACH STATEMENT EXECUTE FUNCTION audit_logs_forbid_modification()
    """,
)

UPGRADE_STATEMENTS = (
    CREATE_USERS,
    CREATE_AUDIT_LOGS,
    *CREATE_AUDIT_INDEXES,
    CREATE_APPEND_ONLY_FUNCTION,
    *CREATE_APPEND_ONLY_TRIGGERS,
)

# Retour en arrière (développement uniquement) : supprime les tables, donc leurs données.
DOWNGRADE_STATEMENTS = (
    "DROP TABLE audit_logs",
    "DROP FUNCTION audit_logs_forbid_modification()",
    "DROP TABLE users",
)


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
