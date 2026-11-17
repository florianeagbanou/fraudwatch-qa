"""Accounts, balances and money movement."""

from decimal import Decimal

import pytest

from qa.schemas import assert_matches


@pytest.mark.smoke
def test_new_account_starts_empty(customer):
    account = customer.open_account(home_country="CA", currency="CAD")

    assert_matches("account", account)
    assert Decimal(str(account["balance"])) == 0
    assert account["owner"] == customer.username


def test_customer_only_lists_own_accounts(customer, other_customer):
    mine = customer.open_account()
    other_customer.open_account()

    ids = [a["id"] for a in customer.get("/api/accounts").json()]

    assert ids == [mine["id"]]


@pytest.mark.parametrize(
    "body",
    [
        {"homeCountry": "Canada", "currency": "CAD"},
        {"homeCountry": "ca", "currency": "CAD"},
        {"homeCountry": "CA", "currency": "dollars"},
        {"currency": "CAD"},
    ],
)
def test_account_input_is_validated(customer, body):
    assert customer.post("/api/accounts", body).status_code == 400


@pytest.mark.smoke
def test_deposit_then_payment_updates_balance(customer, account):
    deposit = customer.transact(account["id"], "DEPOSIT", "250.50")
    assert deposit.status_code == 201
    assert_matches("transaction", deposit.json())

    payment = customer.transact(account["id"], "PAYMENT", "50.25", merchant="Cafe")
    assert payment.status_code == 201

    assert Decimal(str(customer.account(account["id"])["balance"])) == Decimal("200.25")


def test_money_is_exact_to_the_cent(customer, account):
    """0.1 + 0.2 must be 0.30, not 0.30000000000000004 (no floating point for money)."""
    customer.transact(account["id"], "DEPOSIT", "0.10")
    customer.transact(account["id"], "DEPOSIT", "0.20")
    assert Decimal(str(customer.account(account["id"])["balance"])) == Decimal("0.30")


def test_payment_larger_than_balance_is_refused(customer, account):
    customer.transact(account["id"], "DEPOSIT", "100.00")

    response = customer.transact(account["id"], "PAYMENT", "100.01")

    assert response.status_code == 422
    assert response.json()["detail"] == "Insufficient funds"
    assert Decimal(str(customer.account(account["id"])["balance"])) == Decimal("100.00")


def test_paying_the_exact_balance_is_allowed(customer, account):
    customer.transact(account["id"], "DEPOSIT", "100.00")
    assert customer.transact(account["id"], "PAYMENT", "100.00").status_code == 201


@pytest.mark.parametrize(
    ("amount", "why"),
    [("0", "zero"), ("-10", "negative"), ("0.001", "three decimals"), ("1000000.01", "above maximum"), ("abc", "not a number")],
)
def test_invalid_amounts_are_rejected(customer, account, amount, why):
    assert customer.transact(account["id"], "DEPOSIT", amount).status_code == 400, why


def test_unknown_transaction_type_is_rejected(customer, account):
    assert customer.transact(account["id"], "STEAL", "10").status_code == 400


def test_history_is_newest_first(customer, account):
    for amount in ("1.00", "2.00", "3.00"):
        customer.transact(account["id"], "DEPOSIT", amount)

    history = customer.get(f"/api/accounts/{account['id']}/transactions").json()

    assert [Decimal(str(t["amount"])) for t in history] == [Decimal("3.00"), Decimal("2.00"), Decimal("1.00")]
    for transaction in history:
        assert_matches("transaction", transaction)
