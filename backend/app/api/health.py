"""Route de santé du service.

Niveau de permission : 0 (information publique, aucune donnée utilisateur).
Le Policy Engine (étape 6) et l'audit (étape 2) ne sont pas encore implémentés :
cette route ne les utilise donc pas.
"""

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app import SERVICE_NAME, __version__
from app.config import Settings, get_settings

router = APIRouter(tags=["système"])


class HealthResponse(BaseModel):
    """Réponse de /health."""

    status: Literal["ok"]
    service: str
    version: str
    environment: str
    timestamp: datetime


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="État du service",
)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Indique que le processus du backend répond.

    Limite connue : cette route ne vérifie que le processus lui-même. Elle ne teste
    aucune base de données ni service externe, car il n'y en a pas encore (étape 2+).
    """
    return HealthResponse(
        status="ok",
        service=SERVICE_NAME,
        version=__version__,
        environment=settings.environment,
        timestamp=datetime.now(UTC),
    )
