"""Colonne password_hash sur users (authentification, étape 2c).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13

Colonne facultative : un compte sans empreinte de mot de passe ne peut pas se connecter.
Seule l'empreinte (argon2) est stockée, jamais le mot de passe.
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

UPGRADE_STATEMENTS = (
    "ALTER TABLE users ADD COLUMN password_hash text",
    (
        "ALTER TABLE users ADD CONSTRAINT ck_users_password_hash_not_empty "
        "CHECK (password_hash IS NULL OR length(password_hash) > 0)"
    ),
)

# Retour en arrière (développement uniquement) : supprime les empreintes de mots de passe.
DOWNGRADE_STATEMENTS = (
    "ALTER TABLE users DROP CONSTRAINT ck_users_password_hash_not_empty",
    "ALTER TABLE users DROP COLUMN password_hash",
)


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
