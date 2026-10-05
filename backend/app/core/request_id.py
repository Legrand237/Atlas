"""Identifiant de requête (base de l'identifiant de corrélation, règle 41.15).

Chaque requête HTTP reçoit un identifiant, renvoyé dans l'en-tête ``X-Request-ID``
et écrit dans les journaux. Si le client en fournit un valide, il est conservé ;
sinon un nouvel identifiant est généré. La valeur du client est validée pour éviter
d'injecter des caractères inattendus dans les journaux.
"""

import logging
import re
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("atlas.http")

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def resolve_request_id(candidate: str | None) -> str:
    """Retourne ``candidate`` s'il est valide, sinon un nouvel identifiant."""
    if candidate is not None and _VALID_REQUEST_ID.fullmatch(candidate):
        return candidate
    return uuid.uuid4().hex


class RequestIdMiddleware:
    """Attribue un identifiant à chaque requête HTTP et journalise son résultat."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = resolve_request_id(Headers(scope=scope).get(REQUEST_ID_HEADER))
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.perf_counter()
        status_code = 500  # valeur par défaut si une exception interrompt la réponse

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
                request_id,
                scope.get("method"),
                scope.get("path"),
                status_code,
                duration_ms,
            )
