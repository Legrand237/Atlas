"""Tests de la route /health et des briques transverses (identifiant de requête, erreurs)."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app import SERVICE_NAME, __version__
from app.config import Settings, get_settings
from app.main import create_app


@pytest.fixture
def app():
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, environment="test"
    )
    return application


@pytest.fixture
def client(app):
    return TestClient(app)


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == SERVICE_NAME
    assert body["version"] == __version__
    assert body["environment"] == "test"


def test_health_timestamp_is_utc_iso8601(client):
    body = client.get("/health").json()

    parsed = datetime.fromisoformat(body["timestamp"])
    assert parsed.tzinfo is not None
    assert parsed.utcoffset().total_seconds() == 0


def test_health_exposes_only_expected_fields(client):
    body = client.get("/health").json()

    assert set(body) == {"status", "service", "version", "environment", "timestamp"}


def test_health_rejects_non_get_methods(client):
    response = client.post("/health")

    assert response.status_code == 405


def test_unknown_route_returns_404(client):
    response = client.get("/does-not-exist")

    assert response.status_code == 404


def test_response_contains_generated_request_id(client):
    response = client.get("/health")

    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 32


def test_valid_client_request_id_is_kept(client):
    response = client.get("/health", headers={"X-Request-ID": "mon-test_123.abc"})

    assert response.headers["X-Request-ID"] == "mon-test_123.abc"


@pytest.mark.parametrize("bad_value", ["bad id!", "a" * 65, "<script>"])
def test_invalid_client_request_id_is_replaced(client, bad_value):
    response = client.get("/health", headers={"X-Request-ID": bad_value})

    returned = response.headers["X-Request-ID"]
    assert returned != bad_value
    assert len(returned) == 32


def test_unhandled_error_returns_clean_500_without_leaking_details(app):
    @app.get("/boom")
    def boom():
        raise RuntimeError("detail-interne-confidentiel")

    client = TestClient(app, raise_server_exceptions=False)

    response = client.get("/boom", headers={"X-Request-ID": "req-500"})

    assert response.status_code == 500
    assert "detail-interne-confidentiel" not in response.text
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert error["request_id"] == "req-500"
    assert response.headers["X-Request-ID"] == "req-500"
