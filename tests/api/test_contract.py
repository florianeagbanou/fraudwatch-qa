"""The public documentation (OpenAPI) must describe what the API really exposes."""

import pytest

pytestmark = pytest.mark.smoke

EXPECTED_PATHS = {
    "/api/auth/register",
    "/api/auth/login",
    "/api/accounts",
    "/api/accounts/{accountId}",
    "/api/accounts/{accountId}/transactions",
    "/api/alerts",
    "/api/alerts/{alertId}",
    "/api/audit",
}


def test_health_endpoint(anonymous):
    response = anonymous.get("/actuator/health")
    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_openapi_documents_every_endpoint(anonymous):
    spec = anonymous.get("/v3/api-docs").json()
    assert EXPECTED_PATHS <= set(spec["paths"])


def test_openapi_declares_bearer_authentication(anonymous):
    spec = anonymous.get("/v3/api-docs").json()
    scheme = spec["components"]["securitySchemes"]["bearerAuth"]
    assert scheme["type"] == "http"
    assert scheme["scheme"] == "bearer"
