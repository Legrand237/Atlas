"""Route de la passerelle IA : POST /llm/chat (permission niveau 1 : utilisateur connecté).

Cette route envoie le texte reçu au fournisseur (Gemini). Au palier gratuit de Google, ce texte peut être
réutilisé par Google : n'y mets aucune donnée personnelle réelle tant que le palier payant n'est pas actif.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.config import Settings, get_settings
from app.db.models import User
from app.db.session import get_session
from app.llm import service
from app.llm.base import (
    ChatMessage,
    LLMBlocked,
    LLMError,
    LLMNotConfigured,
    LLMProvider,
    LLMRateLimited,
    LLMTimeout,
    LLMUnavailable,
    Role,
    Tier,
)
from app.llm.gemini import GeminiProvider

router = APIRouter(prefix="/llm", tags=["passerelle IA"])

MAX_MESSAGES = 50
MAX_MESSAGE_CHARS = 8000
MAX_TOTAL_CHARS = 32000
MAX_SYSTEM_CHARS = 4000


class MessageIn(BaseModel):
    role: Role
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


class ChatRequest(BaseModel):
    messages: list[MessageIn] = Field(min_length=1, max_length=MAX_MESSAGES)
    system: str | None = Field(default=None, max_length=MAX_SYSTEM_CHARS)
    tier: Tier = "simple"
    max_output_tokens: int | None = Field(default=None, ge=16, le=8192)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)


class UsageOut(BaseModel):
    prompt_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


class ChatResponse(BaseModel):
    text: str
    model: str
    tier: Tier
    finish_reason: str | None
    usage: UsageOut


def get_llm_provider(settings: Annotated[Settings, Depends(get_settings)]) -> LLMProvider:
    """Fournisseur configuré ; 503 si la clé manque. (Les tests remplacent cette dépendance.)"""
    if settings.gemini_api_key is None:
        raise HTTPException(status_code=503, detail="Passerelle IA non configurée (GEMINI_API_KEY manquante).")
    return GeminiProvider(settings.gemini_api_key.get_secret_value(), timeout_seconds=settings.llm_timeout_seconds)


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LLMNotConfigured):
        return HTTPException(503, "Passerelle IA non configurée pour ce niveau.")
    if isinstance(exc, service.DailyLimitReached):
        return HTTPException(429, f"Plafond journalier atteint ({exc.kind}).", headers={"Retry-After": "3600"})
    if isinstance(exc, LLMRateLimited):
        headers = {"Retry-After": str(exc.retry_after_seconds)} if exc.retry_after_seconds else None
        return HTTPException(429, "Quota du fournisseur IA dépassé. Réessaie plus tard.", headers=headers)
    if isinstance(exc, LLMBlocked):
        return HTTPException(422, "Contenu refusé par les filtres du fournisseur IA.")
    if isinstance(exc, LLMTimeout):
        return HTTPException(504, "Le fournisseur IA n'a pas répondu à temps.")
    if isinstance(exc, LLMUnavailable):
        return HTTPException(503, "Fournisseur IA indisponible.")
    return HTTPException(502, "Réponse du fournisseur IA inutilisable ou refusée.")


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[LLMProvider, Depends(get_llm_provider)],
) -> ChatResponse:
    """Envoie la conversation au modèle du niveau demandé et retourne sa réponse."""
    if sum(len(m.content) for m in body.messages) > MAX_TOTAL_CHARS:
        raise HTTPException(413, f"Conversation trop longue ({MAX_TOTAL_CHARS} caractères au maximum).")
    if body.messages[-1].role != "user":
        raise HTTPException(422, "Le dernier message doit venir de l'utilisateur.")
    correlation_id = getattr(request.state, "request_id", None) or uuid.uuid4().hex
    try:
        result = service.chat(
            session, provider, settings,
            user_id=user.id, correlation_id=correlation_id, tier=body.tier,
            messages=[ChatMessage(m.role, m.content) for m in body.messages],
            system=body.system, max_output_tokens=body.max_output_tokens, temperature=body.temperature,
        )  # fmt: skip
    except (LLMError, service.DailyLimitReached) as exc:
        raise _http_error(exc) from None
    return ChatResponse(
        text=result.text, model=result.model, tier=body.tier, finish_reason=result.finish_reason,
        usage=UsageOut(
            prompt_tokens=result.prompt_tokens, output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
        ),
    )  # fmt: skip
