"""Configuration de l'application, lue depuis les variables d'environnement.

Règles :
- aucun secret n'est écrit dans le code ;
- les valeurs viennent de l'environnement ou d'un fichier ``.env`` local (ignoré par Git) ;
- une valeur invalide fait échouer le démarrage immédiatement (échec explicite plutôt que
  comportement silencieusement incorrect).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de l'application.

    ``database_url`` est un secret (il contient le mot de passe de la base) : il est lu
    uniquement depuis l'environnement / ``.env`` et n'apparaît jamais dans les journaux.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    database_url: SecretStr | None = None
    # Authentification (étape 2c). Sans JWT_SECRET_KEY, l'API démarre mais /auth/login répond 503.
    jwt_secret_key: SecretStr | None = None
    session_duration_minutes: int = Field(default=60, ge=5, le=1440)
    login_max_failures: int = Field(default=5, ge=1, le=50)
    login_window_minutes: int = Field(default=15, ge=1, le=1440)

    @field_validator("jwt_secret_key", mode="before")
    @classmethod
    def _check_jwt_secret_key(cls, value):
        """Vide = non configurée ; sinon au moins 32 caractères (clé de signature des tokens)."""
        if value is None:
            return None
        raw = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        raw = raw.strip()
        if raw == "":
            return None
        if len(raw) < 32:
            raise ValueError("JWT_SECRET_KEY doit contenir au moins 32 caractères.")
        return raw

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value):
        """Accepte l'adresse telle que la donne le fournisseur (postgresql://...).

        Elle est convertie pour utiliser le pilote ``psycopg`` (version 3). Une valeur vide
        signifie « base non configurée ». Une adresse qui n'est pas PostgreSQL est refusée.
        """
        if value is None:
            return None
        raw = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        raw = raw.strip()
        if raw == "":
            return None
        for prefix in ("postgresql://", "postgres://"):
            if raw.startswith(prefix):
                return "postgresql+psycopg://" + raw[len(prefix) :]
        if raw.startswith("postgresql+psycopg://"):
            return raw
        raise ValueError("DATABASE_URL doit commencer par postgresql://")


@lru_cache
def get_settings() -> Settings:
    """Retourne les paramètres (lus une seule fois, puis mis en cache)."""
    return Settings()
