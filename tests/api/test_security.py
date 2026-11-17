"""Authorization and common web API weaknesses (OWASP API Security Top 10)."""

import base64
import json

import pytest

from qa.client import ApiClient

pytestmark = pytest.mark.security


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/accounts"),
        ("POST", "/api/accounts"),
        ("GET", "/api/alerts"),
        ("GET", "/api/audit"),
    ],
)
def test_protected_routes_need_a_token(anonymous, method, path):
    assert anonymous.request(method, path).status_code == 401


def test_garbage_token_is_rejected(customer):
    customer.token = "not-a-jwt"
    assert customer.get("/api/accounts").status_code == 401


def test_tampered_token_is_rejected(customer):
    """Change the role inside the token without re-signing it: the signature check must catch it."""
    header, payload, signature = customer.token.split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    claims["roles"] = ["ADMIN"]
    forged = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    customer.token = f"{header}.{forged}.{signature}"

    assert customer.get("/api/audit").status_code == 401


def test_unsigned_token_is_rejected(customer):
    """The classic "alg: none" attack."""
    def b64(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    customer.token = f"{b64({'alg': 'none'})}.{b64({'sub': 'admin', 'roles': ['ADMIN'], 'iss': 'fraudwatch-api'})}."
    assert customer.get("/api/audit").status_code == 401


# --- Broken object level authorization (IDOR) ------------------------------------------


def test_cannot_read_someone_elses_account(customer, other_customer):
    victim_account = other_customer.open_account()
    assert customer.get(f"/api/accounts/{victim_account['id']}").status_code == 404


def test_cannot_read_someone_elses_transactions(customer, other_customer):
    victim_account = other_customer.open_account()
    assert customer.get(f"/api/accounts/{victim_account['id']}/transactions").status_code == 404


def test_cannot_spend_from_someone_elses_account(customer, other_customer):
    victim_account = other_customer.open_account()
    other_customer.transact(victim_account["id"], "DEPOSIT", "500.00")

    response = customer.transact(victim_account["id"], "WITHDRAWAL", "500.00")

    assert response.status_code == 404
    assert other_customer.account(victim_account["id"])["balance"] == 500.0


def test_account_numbers_are_not_sequential(customer):
    numbers = [int(customer.open_account()["number"][3:]) for _ in range(3)]
    assert sorted(numbers) != list(range(numbers[0], numbers[0] + 3))


# --- Broken function level authorization ------------------------------------------------


def test_customer_cannot_use_analyst_routes(customer):
    assert customer.get("/api/alerts").status_code == 403
    assert customer.patch("/api/alerts/1", {"resolution": "FALSE_POSITIVE"}).status_code == 403


def test_customer_cannot_read_audit_log(customer):
    assert customer.get("/api/audit").status_code == 403


def test_analyst_cannot_read_audit_log(analyst):
    assert analyst.get("/api/audit").status_code == 403


def test_analyst_cannot_open_customer_accounts(analyst):
    assert analyst.post("/api/accounts", {"homeCountry": "CA", "currency": "CAD"}).status_code == 403


def test_admin_sees_security_events(admin, anonymous):
    anonymous.login("analyst", "WrongPass1")  # generates a LOGIN_FAILURE event

    events = admin.get("/api/audit", params={"limit": 20}).json()

    assert any(e["action"] == "LOGIN_FAILURE" and e["actor"] == "analyst" for e in events)


# --- Injection and data exposure ------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    ["' OR '1'='1", "Robert'); DROP TABLE account;--", "<img src=x onerror=alert(1)>", "${jndi:ldap://x/a}"],
)
def test_hostile_merchant_names_are_stored_as_plain_text(customer, funded_account, payload):
    response = customer.transact(funded_account["id"], "PAYMENT", "1.00", merchant=payload)

    assert response.status_code == 201
    assert response.json()["merchant"] == payload  # stored as data, not executed
    assert customer.get("/api/accounts").status_code == 200  # tables still there


def test_errors_do_not_leak_internals(customer):
    response = customer.get("/api/accounts/not-a-number")
    assert response.status_code == 400
    for leak in ("Exception", "at com.", "org.springframework", "SQL", "Hibernate"):
        assert leak not in response.text


def test_security_headers_on_the_web_ui(anonymous):
    headers = ApiClient().get("/").headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert "Content-Security-Policy" in headers
    assert headers.get("X-Frame-Options") in ("DENY", "SAMEORIGIN")
