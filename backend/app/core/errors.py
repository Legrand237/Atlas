"""Gestion des erreurs : réponses JSON claires, sans fuite de détails internes."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.request_id import REQUEST_ID_HEADER

logger = logging.getLogger("atlas.errors")


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Répond 500 sans exposer la pile d'appels ni le message de l'exception.

    Le détail complet est écrit dans les journaux du serveur, avec l'identifiant de requête.
    """
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        "Erreur non gérée request_id=%s path=%s",
        request_id,
        request.url.path,
        exc_info=exc,
    )
    headers = {REQUEST_ID_HEADER: request_id} if request_id else None
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "Erreur interne du serveur.",
                "request_id": request_id,
            }
        },
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Enregistre les gestionnaires d'erreurs de l'application."""
    app.add_exception_handler(Exception, unhandled_exception_handler)
