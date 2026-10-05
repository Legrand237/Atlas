"""Point d'entrée de l'application FastAPI Atlas.

Lancer en développement (depuis le dossier backend/) :
    uvicorn app.main:app --reload
"""

import logging

from fastapi import FastAPI

from app import SERVICE_NAME, __version__
from app.api.health import router as health_router
from app.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.request_id import RequestIdMiddleware


def create_app() -> FastAPI:
    """Construit l'application (fonction séparée pour pouvoir la tester)."""
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    app = FastAPI(
        title="Atlas",
        description="Backend de l'agent IA personnel Atlas.",
        version=__version__,
    )
    app.add_middleware(RequestIdMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router)

    logging.getLogger("atlas").info(
        "%s %s démarré (environment=%s)", SERVICE_NAME, __version__, settings.environment
    )
    return app


app = create_app()
