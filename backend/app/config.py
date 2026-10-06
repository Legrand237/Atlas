"""Configuration de l'application, lue depuis les variables d'environnement.

Règles :
- aucun secret n'est écrit dans le code ;
- les valeurs viennent de l'environnement ou d'un fichier ``.env`` local (ignoré par Git) ;
- une valeur invalide fait échouer le démarrage immédiatement (échec explicite plutôt que
  comportement silencieusement incorrect).
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator
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
