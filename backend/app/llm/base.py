"""Types communs de la passerelle IA : messages, résultat, erreurs et interface d'un fournisseur.

L'agent (étapes suivantes) ne dépend que de ce module : changer de fournisseur ne touche pas l'agent.
Aucun message d'erreur ne contient la clé d'API ni le contenu des conversations.
"""

import re
from dataclasses import dataclass
from typing import Literal, Protocol

Role = Literal["user", "assistant"]
Tier = Literal["simple", "medium", "hard"]
TIERS: tuple[str, ...] = ("simple", "medium", "hard")

# Un nom de modèle va dans l'adresse de l'API : on n'accepte que des caractères sûrs.
MODEL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


@dataclass(frozen=True)
class ChatMessage:
    role: Role
    content: str


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    finish_reason: str | None
    prompt_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


class LLMError(Exception):
    """Erreur de la passerelle IA. ``code`` est un identifiant stable, sans donnée sensible."""

    code = "llm_error"


class LLMNotConfigured(LLMError):
    """Clé d'API ou modèle non configuré."""

    code = "llm_not_configured"


class LLMRejected(LLMError):
    """Le fournisseur refuse la requête (clé invalide, modèle inconnu, requête mal formée)."""

    code = "llm_rejected"

    def __init__(self, provider_status: str | None = None) -> None:
        super().__init__(provider_status or "rejected")
        self.provider_status = provider_status


class LLMRateLimited(LLMError):
    """Quota du fournisseur dépassé (HTTP 429)."""

    code = "llm_rate_limited"

    def __init__(self, retry_after_seconds: int | None = None) -> None:
        super().__init__("rate_limited")
        self.retry_after_seconds = retry_after_seconds


class LLMUnavailable(LLMError):
    """Fournisseur injoignable ou en erreur (réseau, 5xx)."""

    code = "llm_unavailable"


class LLMTimeout(LLMUnavailable):
    """Le fournisseur n'a pas répondu à temps."""

    code = "llm_timeout"


class LLMBlocked(LLMError):
    """Réponse bloquée par les filtres de sécurité du fournisseur."""

    code = "llm_blocked"


class LLMBadResponse(LLMError):
    """Réponse du fournisseur inattendue ou vide."""

    code = "llm_bad_response"


class LLMProvider(Protocol):
    name: str

    def generate(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        system: str | None,
        max_output_tokens: int,
        temperature: float | None,
    ) -> LLMResult: ...
