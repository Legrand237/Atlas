"""Service d'appel au modèle : niveau → modèle, plafonds journaliers, audit de chaque appel.

Chaque appel au fournisseur (réussi ou non) est écrit dans ``audit_logs`` (action ``llm_chat``) avec
l'identifiant de corrélation de la requête : modèle, niveau, volumes de jetons, durée. Ni le contenu
des messages, ni la clé, ni la réponse n'y sont écrits. Un appel refusé par un plafond est audité
(``denied``) mais n'est pas compté dans les plafonds.

Les plafonds se calculent sur les 24 dernières heures à partir du journal d'audit. Ils sont vérifiés
AVANT l'appel : un appel peut donc dépasser légèrement le plafond de jetons (jamais celui de requêtes).
"""

import time
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.db.audit import record_event
from app.db.models import AuditLog
from app.llm.base import ChatMessage, LLMError, LLMNotConfigured, LLMProvider, LLMResult

ACTION = "llm_chat"
PERMISSION_LEVEL = 1  # utilisateur connecté


class DailyLimitReached(Exception):
    """Plafond journalier de requêtes ou de jetons atteint."""

    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind  # "requests" ou "tokens"


def _usage_last_24h(session: Session, user_id: uuid.UUID) -> tuple[int, int]:
    since = datetime.now(UTC) - timedelta(hours=24)
    requests, tokens = session.execute(
        select(
            func.count(),
            func.coalesce(func.sum(AuditLog.details["usage"]["total"].as_integer()), 0),
        ).where(
            AuditLog.user_id == user_id,
            AuditLog.action == ACTION,
            AuditLog.result.in_(("success", "failure")),
            AuditLog.occurred_at > since,
        )
    ).one()
    return int(requests), int(tokens)


def chat(
    session: Session,
    provider: LLMProvider,
    settings: Settings,
    *,
    user_id: uuid.UUID,
    correlation_id: str,
    tier: str,
    messages: list[ChatMessage],
    system: str | None,
    max_output_tokens: int | None,
    temperature: float | None,
) -> LLMResult:
    """Appelle le modèle du niveau demandé. Lève ``LLMNotConfigured``, ``DailyLimitReached`` ou ``LLMError``."""
    model = settings.model_for_tier(tier)
    if model is None:
        raise LLMNotConfigured(f"Aucun modèle configuré pour le niveau {tier}.")

    requests, tokens = _usage_last_24h(session, user_id)
    exceeded = (
        "requests" if requests >= settings.llm_daily_request_limit
        else "tokens" if tokens >= settings.llm_daily_token_limit
        else None
    )  # fmt: skip
    if exceeded is not None:
        record_event(
            session, correlation_id=correlation_id, actor_type="user", user_id=user_id, action=ACTION,
            tool=provider.name, permission_level=PERMISSION_LEVEL, authorization_decision="denied",
            decision_reason=f"daily_{exceeded}_limit", result="denied",
            details={"tier": tier, "model": model},
        )  # fmt: skip
        session.commit()
        raise DailyLimitReached(exceeded)

    output_cap = min(max_output_tokens or settings.llm_max_output_tokens, settings.llm_max_output_tokens)
    started = time.monotonic()
    try:
        result = provider.generate(
            model=model, messages=messages, system=system,
            max_output_tokens=output_cap, temperature=temperature,
        )  # fmt: skip
    except LLMError as exc:
        record_event(
            session, correlation_id=correlation_id, actor_type="user", user_id=user_id, action=ACTION,
            tool=provider.name, permission_level=PERMISSION_LEVEL, authorization_decision="allowed",
            decision_reason="within_daily_limits", result="failure", error=exc.code,
            details={"tier": tier, "model": model, "duration_ms": int((time.monotonic() - started) * 1000)},
        )  # fmt: skip
        session.commit()
        raise

    record_event(
        session, correlation_id=correlation_id, actor_type="user", user_id=user_id, action=ACTION,
        tool=provider.name, permission_level=PERMISSION_LEVEL, authorization_decision="allowed",
        decision_reason="within_daily_limits", result="success",
        details={
            "tier": tier,
            "model": model,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "usage": {
                "prompt": result.prompt_tokens or 0,
                "output": result.output_tokens or 0,
                "total": result.total_tokens or 0,
            },
        },
    )  # fmt: skip
    session.commit()
    return result
