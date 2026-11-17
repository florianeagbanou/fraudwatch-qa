"""Fixtures shared by every test."""

import pytest
import requests

from qa.client import ApiClient
from qa.config import ADMIN, ANALYST, BASE_URL


def pytest_sessionstart(session):
    """Fail fast with a clear message if the API is not running, instead of 100 confusing errors."""
    try:
        requests.get(f"{BASE_URL}/actuator/health", timeout=5).raise_for_status()
    except requests.RequestException as exc:
        pytest.exit(f"FraudWatch API not reachable at {BASE_URL} ({exc}). Start it or set BASE_URL.", returncode=2)


@pytest.fixture
def anonymous() -> ApiClient:
    return ApiClient()


@pytest.fixture
def customer() -> ApiClient:
    """A brand-new logged-in customer for each test."""
    return ApiClient().sign_up_and_login()


@pytest.fixture
def other_customer() -> ApiClient:
    return ApiClient().sign_up_and_login()


@pytest.fixture
def account(customer) -> dict:
    return customer.open_account()


@pytest.fixture
def funded_account(customer) -> dict:
    """An account with 1 000 $ deposited in its home country."""
    acc = customer.open_account()
    assert customer.transact(acc["id"], "DEPOSIT", "1000.00").status_code == 201
    return acc


@pytest.fixture
def analyst() -> ApiClient:
    client = ApiClient()
    assert client.login(*ANALYST).status_code == 200
    return client


@pytest.fixture
def admin() -> ApiClient:
    client = ApiClient()
    assert client.login(*ADMIN).status_code == 200
    return client
