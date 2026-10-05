"""Configuration de l'application, lue depuis les variables d'environnement.

Règles :
- aucun secret n'est écrit dans le code ;
- les valeurs viennent de l'environnement ou d'un fichier ``.env`` local (ignoré par Git) ;
- une valeur invalide fait échouer le démarrage immédiatement (échec explicite plutôt que
  comportement silencieusement incorrect).
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de l'application (étape 1 : aucun secret nécessaire)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Retourne les paramètres (lus une seule fois, puis mis en cache)."""
    return Settings()
