"""A thin wrapper around requests so tests read like business steps, not HTTP plumbing."""

from __future__ import annotations

import uuid

import requests

from qa.config import BASE_URL, DEFAULT_PASSWORD

TIMEOUT = 10  # seconds: a hanging API must fail the test, not block the pipeline


def unique_username(prefix: str = "qa") -> str:
    """Each test creates its own users, so tests never depend on each other or on run order."""
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


class ApiClient:
    def __init__(self, base_url: str = BASE_URL, token: str | None = None):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = token
        self.username: str | None = None

    # -- low level ---------------------------------------------------------

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        headers = kwargs.pop("headers", {})
        if self.token and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {self.token}"
        return self.session.request(method, self.base_url + path, headers=headers, timeout=TIMEOUT, **kwargs)

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, json=None, **kwargs) -> requests.Response:
        return self.request("POST", path, json=json, **kwargs)

    def patch(self, path: str, json=None, **kwargs) -> requests.Response:
        return self.request("PATCH", path, json=json, **kwargs)

    # -- business steps ----------------------------------------------------

    def register(self, username: str, password: str = DEFAULT_PASSWORD) -> requests.Response:
        return self.post("/api/auth/register", {"username": username, "password": password})

    def login(self, username: str, password: str = DEFAULT_PASSWORD) -> requests.Response:
        response = self.post("/api/auth/login", {"username": username, "password": password})
        if response.status_code == 200:
            self.token = response.json()["accessToken"]
            self.username = username
        return response

    def sign_up_and_login(self) -> ApiClient:
        username = unique_username()
        assert self.register(username).status_code == 201
        assert self.login(username).status_code == 200
        return self

    def open_account(self, home_country: str = "CA", currency: str = "CAD") -> dict:
        response = self.post("/api/accounts", {"homeCountry": home_country, "currency": currency})
        assert response.status_code == 201, response.text
        return response.json()

    def transact(self, account_id: int, type_: str, amount, country: str = "CA", merchant: str | None = None):
        body = {"type": type_, "amount": str(amount), "country": country}
        if merchant:
            body["merchant"] = merchant
        return self.post(f"/api/accounts/{account_id}/transactions", body)

    def account(self, account_id: int) -> dict:
        response = self.get(f"/api/accounts/{account_id}")
        assert response.status_code == 200, response.text
        return response.json()

    def alerts(self, status: str | None = "OPEN") -> list[dict]:
        response = self.get("/api/alerts", params={"status": status} if status else None)
        assert response.status_code == 200, response.text
        return response.json()

    def alert_for(self, transaction_id: int) -> dict:
        matches = [a for a in self.alerts(status=None) if a["transactionId"] == transaction_id]
        assert matches, f"no alert for transaction {transaction_id}"
        return matches[0]

    def review(self, alert_id: int, resolution: str, note: str = "QA review") -> requests.Response:
        return self.patch(f"/api/alerts/{alert_id}", {"resolution": resolution, "note": note})
