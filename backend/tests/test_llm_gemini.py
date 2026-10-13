"""Tests de l'adaptateur Gemini avec un transport HTTP de test (httpx.MockTransport).

IMPORTANT : ces tests vérifient la construction de la requête et la lecture des réponses telles que la
documentation de Google les décrit. Ils NE prouvent PAS que Google répond ainsi : seule la commande
``python -m app.llm_check ping simple`` (clé réelle) le prouve. Voir docs/ETAPE3_GUIDE.md.
"""

import json

import httpx
import pytest

from app.llm.base import (
    ChatMessage,
    LLMBadResponse,
    LLMBlocked,
    LLMNotConfigured,
    LLMRateLimited,
    LLMRejected,
    LLMTimeout,
    LLMUnavailable,
)
from app.llm.gemini import GeminiProvider

KEY = "cle-de-test-sans-valeur-0123456789"
OK_BODY = {
    "candidates": [{"content": {"parts": [{"text": "Bonjour"}]}, "finishReason": "STOP"}],
    "usageMetadata": {"promptTokenCount": 7, "candidatesTokenCount": 3, "totalTokenCount": 10},
}


def _provider(handler) -> GeminiProvider:
    return GeminiProvider(KEY, base_url="https://exemple.test/v1beta", transport=httpx.MockTransport(handler))


def _generate(provider: GeminiProvider, **overrides):
    args = {
        "model": "modele-test",
        "messages": [ChatMessage("user", "Salut")],
        "system": None,
        "max_output_tokens": 50,
        "temperature": None,
    }
    args.update(overrides)
    return provider.generate(**args)


def test_request_format_and_key_in_header_only():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["method"] = request.method
        seen["key_header"] = request.headers.get("x-goog-api-key")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=OK_BODY)

    result = _generate(
        _provider(handler),
        messages=[ChatMessage("user", "Q1"), ChatMessage("assistant", "R1"), ChatMessage("user", "Q2")],
        system="Sois bref.",
        temperature=0.2,
    )

    assert seen["method"] == "POST"
    assert seen["url"] == "https://exemple.test/v1beta/models/modele-test:generateContent"
    assert KEY not in seen["url"]
    assert seen["key_header"] == KEY
    assert [c["role"] for c in seen["body"]["contents"]] == ["user", "model", "user"]
    assert seen["body"]["contents"][2]["parts"] == [{"text": "Q2"}]
    assert seen["body"]["systemInstruction"] == {"parts": [{"text": "Sois bref."}]}
    assert seen["body"]["generationConfig"] == {"maxOutputTokens": 50, "temperature": 0.2}
    assert (result.text, result.model, result.finish_reason) == ("Bonjour", "modele-test", "STOP")
    assert (result.prompt_tokens, result.output_tokens, result.total_tokens) == (7, 3, 10)


def test_no_system_and_no_temperature_are_omitted():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=OK_BODY)

    _generate(_provider(handler))
    assert "systemInstruction" not in seen["body"]
    assert seen["body"]["generationConfig"] == {"maxOutputTokens": 50}


def test_thought_parts_are_not_returned():
    body = {
        "candidates": [
            {"content": {"parts": [{"text": "réflexion", "thought": True}, {"text": "Réponse "}, {"text": "finale"}]}}
        ]
    }
    result = _generate(_provider(lambda r: httpx.Response(200, json=body)))
    assert result.text == "Réponse finale"
    assert result.total_tokens is None  # pas de usageMetadata : inconnu, pas inventé


def test_rate_limit_with_retry_after():
    handler = lambda r: httpx.Response(429, headers={"Retry-After": "17"}, json={"error": {"status": "RESOURCE_EXHAUSTED"}})
    with pytest.raises(LLMRateLimited) as info:
        _generate(_provider(handler))
    assert info.value.retry_after_seconds == 17


def test_rate_limit_without_retry_after():
    with pytest.raises(LLMRateLimited) as info:
        _generate(_provider(lambda r: httpx.Response(429, json={})))
    assert info.value.retry_after_seconds is None


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_client_errors_are_rejections_with_short_status(status):
    body = {"error": {"status": "INVALID_ARGUMENT", "message": f"détail libre avec {KEY}"}}
    with pytest.raises(LLMRejected) as info:
        _generate(_provider(lambda r: httpx.Response(status, json=body)))
    assert info.value.provider_status == "INVALID_ARGUMENT"
    assert KEY not in str(info.value)


def test_rejection_with_unreadable_body():
    with pytest.raises(LLMRejected) as info:
        _generate(_provider(lambda r: httpx.Response(400, text="<html>")))
    assert info.value.provider_status is None


@pytest.mark.parametrize("status", [500, 502, 503])
def test_server_errors_are_unavailable(status):
    with pytest.raises(LLMUnavailable):
        _generate(_provider(lambda r: httpx.Response(status)))


def test_timeout_and_network_error():
    def timeout(request):
        raise httpx.ReadTimeout("lent", request=request)

    def broken(request):
        raise httpx.ConnectError("coupé", request=request)

    with pytest.raises(LLMTimeout):
        _generate(_provider(timeout))
    with pytest.raises(LLMUnavailable) as info:
        _generate(_provider(broken))
    assert not isinstance(info.value, LLMTimeout)


def test_blocked_prompt_and_blocked_response():
    blocked_prompt = {"promptFeedback": {"blockReason": "SAFETY"}}
    with pytest.raises(LLMBlocked):
        _generate(_provider(lambda r: httpx.Response(200, json=blocked_prompt)))
    blocked_answer = {"candidates": [{"finishReason": "SAFETY"}]}
    with pytest.raises(LLMBlocked):
        _generate(_provider(lambda r: httpx.Response(200, json=blocked_answer)))


@pytest.mark.parametrize(
    "body",
    [{}, {"candidates": []}, {"candidates": [{"content": {"parts": [{"text": "  "}]}, "finishReason": "STOP"}]}, []],
)
def test_unusable_responses(body):
    with pytest.raises(LLMBadResponse):
        _generate(_provider(lambda r: httpx.Response(200, json=body)))


def test_invalid_json_response():
    with pytest.raises(LLMBadResponse):
        _generate(_provider(lambda r: httpx.Response(200, text="pas du json")))


def test_missing_key_and_bad_model_name_and_no_messages():
    with pytest.raises(LLMNotConfigured):
        GeminiProvider("")
    provider = _provider(lambda r: httpx.Response(200, json=OK_BODY))
    for bad in ("../x", "a/b", "a b", "", "x?y=1"):
        with pytest.raises(LLMNotConfigured):
            _generate(provider, model=bad)
    with pytest.raises(LLMBadResponse):
        _generate(provider, messages=[])


def test_list_models_filters_sorts_and_paginates():
    pages = {
        None: {
            "models": [
                {"name": "models/zeta", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/embed", "supportedGenerationMethods": ["embedContent"]},
            ],
            "nextPageToken": "p2",
        },
        "p2": {"models": [{"name": "models/alpha", "supportedGenerationMethods": ["generateContent", "countTokens"]}]},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-goog-api-key"] == KEY
        assert KEY not in str(request.url)
        return httpx.Response(200, json=pages[request.url.params.get("pageToken")])

    assert _provider(handler).list_models() == ["alpha", "zeta"]
