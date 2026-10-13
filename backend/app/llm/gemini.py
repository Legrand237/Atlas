"""Adaptateur Google Gemini (API REST ``generateContent``, version ``v1beta``).

La clé est envoyée dans l'en-tête ``x-goog-api-key`` (jamais dans l'adresse, donc jamais dans les journaux).
ATTENTION : ce module n'a pas encore été vérifié par un appel réel à Google (réseau bloqué dans
l'environnement de construction) ; voir docs/ETAPE3_GUIDE.md pour la vérification réelle.
"""

import httpx

from app.llm.base import (
    MODEL_NAME_PATTERN,
    ChatMessage,
    LLMBadResponse,
    LLMBlocked,
    LLMNotConfigured,
    LLMRateLimited,
    LLMRejected,
    LLMResult,
    LLMTimeout,
    LLMUnavailable,
)

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_BLOCKED_FINISH_REASONS = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION", "IMAGE_SAFETY"}


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _provider_status(response: httpx.Response) -> str | None:
    """Champ ``error.status`` (ex. RESOURCE_EXHAUSTED) : un code court, jamais le message libre."""
    try:
        status = response.json()["error"]["status"]
    except (ValueError, KeyError, TypeError):
        return None
    return status if isinstance(status, str) and len(status) <= 64 else None


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: float = 30.0,
        base_url: str = DEFAULT_BASE_URL,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise LLMNotConfigured("GEMINI_API_KEY manquante.")
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._base_url = base_url.rstrip("/")
        self._transport = transport

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.request(
                    method, f"{self._base_url}{path}", headers={"x-goog-api-key": self._api_key}, **kwargs
                )
        except httpx.TimeoutException:
            raise LLMTimeout("timeout") from None
        except httpx.HTTPError:
            raise LLMUnavailable("network_error") from None
        self._raise_for_status(response)
        return response

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        code = response.status_code
        if code < 400:
            return
        if code == 429:
            retry_after = response.headers.get("Retry-After", "")
            raise LLMRateLimited(int(retry_after) if retry_after.isdigit() else None)
        if code >= 500:
            status = _provider_status(response)
            raise LLMUnavailable(f"http_{code}" + (f" ({status})" if status else ""))
        raise LLMRejected(_provider_status(response))

    def list_models(self) -> list[str]:
        """Noms des modèles (sans le préfixe ``models/``) qui acceptent ``generateContent``."""
        names: list[str] = []
        page_token: str | None = None
        for _ in range(20):  # garde-fou contre une pagination sans fin
            params: dict[str, str | int] = {"pageSize": 100}
            if page_token:
                params["pageToken"] = page_token
            data = self._json(self._request("GET", "/models", params=params))
            for model in data.get("models", []):
                name = model.get("name", "")
                if "generateContent" in model.get("supportedGenerationMethods", []) and name.startswith("models/"):
                    names.append(name.removeprefix("models/"))
            page_token = data.get("nextPageToken")
            if not page_token:
                break
        return sorted(names)

    @staticmethod
    def _json(response: httpx.Response) -> dict:
        try:
            data = response.json()
        except ValueError:
            raise LLMBadResponse("invalid_json") from None
        if not isinstance(data, dict):
            raise LLMBadResponse("invalid_json")
        return data

    def generate(
        self,
        *,
        model: str,
        messages: list[ChatMessage],
        system: str | None,
        max_output_tokens: int,
        temperature: float | None,
    ) -> LLMResult:
        if not MODEL_NAME_PATTERN.match(model):
            raise LLMNotConfigured("Nom de modèle invalide.")
        if not messages:
            raise LLMBadResponse("no_messages")
        generation_config: dict[str, object] = {"maxOutputTokens": max_output_tokens}
        if temperature is not None:
            generation_config["temperature"] = temperature
        body: dict[str, object] = {
            "contents": [
                {"role": "model" if m.role == "assistant" else "user", "parts": [{"text": m.content}]}
                for m in messages
            ],
            "generationConfig": generation_config,
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}

        data = self._json(self._request("POST", f"/models/{model}:generateContent", json=body))
        return self._parse(data, model)

    @staticmethod
    def _parse(data: dict, model: str) -> LLMResult:
        usage = data.get("usageMetadata") if isinstance(data.get("usageMetadata"), dict) else {}
        candidates = data.get("candidates")
        if not candidates:
            feedback = data.get("promptFeedback")
            if isinstance(feedback, dict) and feedback.get("blockReason"):
                raise LLMBlocked("prompt_blocked")
            raise LLMBadResponse("no_candidates")
        candidate = candidates[0] if isinstance(candidates[0], dict) else {}
        finish_reason = candidate.get("finishReason") if isinstance(candidate.get("finishReason"), str) else None
        content = candidate.get("content") if isinstance(candidate.get("content"), dict) else {}
        parts = content.get("parts") if isinstance(content.get("parts"), list) else []
        text = "".join(
            part["text"]
            for part in parts
            if isinstance(part, dict) and isinstance(part.get("text"), str) and not part.get("thought")
        )
        if not text.strip():
            if finish_reason in _BLOCKED_FINISH_REASONS:
                raise LLMBlocked("response_blocked")
            raise LLMBadResponse("empty_response")
        return LLMResult(
            text=text,
            model=model,
            finish_reason=finish_reason,
            prompt_tokens=_int_or_none(usage.get("promptTokenCount")),
            output_tokens=_int_or_none(usage.get("candidatesTokenCount")),
            total_tokens=_int_or_none(usage.get("totalTokenCount")),
        )
