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

from app.llm.base import MODEL_NAME_PATTERN


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

    # Passerelle IA (étape 3). Sans GEMINI_API_KEY ou sans modèle du niveau demandé, /llm/chat répond 503.
    gemini_api_key: SecretStr | None = None
    llm_model_simple: str | None = None
    llm_model_medium: str | None = None
    llm_model_hard: str | None = None
    llm_daily_request_limit: int = Field(default=200, ge=1, le=10000)
    llm_daily_token_limit: int = Field(default=200000, ge=1000, le=10000000)
    llm_max_output_tokens: int = Field(default=1024, ge=16, le=8192)
    llm_timeout_seconds: float = Field(default=30.0, ge=5.0, le=120.0)

    @field_validator("gemini_api_key", mode="before")
    @classmethod
    def _empty_gemini_key_is_none(cls, value):
        if value is None:
            return None
        raw = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        raw = raw.strip()
        return raw or None

    @field_validator("llm_model_simple", "llm_model_medium", "llm_model_hard", mode="before")
    @classmethod
    def _check_model_name(cls, value):
        """Vide = non configuré ; sinon uniquement lettres, chiffres, point, tiret, souligné."""
        if value is None:
            return None
        raw = str(value).strip()
        if raw == "":
            return None
        if not MODEL_NAME_PATTERN.match(raw):
            raise ValueError("Nom de modèle invalide (lettres, chiffres, . - _ uniquement).")
        return raw

    def model_for_tier(self, tier: str) -> str | None:
        return {"simple": self.llm_model_simple, "medium": self.llm_model_medium, "hard": self.llm_model_hard}[tier]

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
