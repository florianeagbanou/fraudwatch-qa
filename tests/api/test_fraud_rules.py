"""Black-box checks of each fraud rule, through the public API only."""

from decimal import Decimal

import pytest

from qa.oracle import assert_assessment

pytestmark = pytest.mark.fraud


def test_normal_home_deposit_is_approved(customer, account):
    tx = customer.transact(account["id"], "DEPOSIT", "100.00").json()
    assert_assessment(tx, set())


def test_large_amount(customer, account):
    tx = customer.transact(account["id"], "DEPOSIT", "10000.00").json()
    assert_assessment(tx, {"LARGE_AMOUNT"})


def test_just_below_large_amount(customer, account):
    tx = customer.transact(account["id"], "DEPOSIT", "9999.99").json()
    assert_assessment(tx, set())


def test_foreign_country_alone_is_low_risk(customer, account):
    """First transaction ever, abroad: foreign country, but no previous country to compare with."""
    tx = customer.transact(account["id"], "DEPOSIT", "50.00", country="FR").json()
    assert_assessment(tx, {"FOREIGN_COUNTRY"})


def test_impossible_travel(customer, funded_account):
    tx = customer.transact(funded_account["id"], "PAYMENT", "20.00", country="JP").json()
    assert_assessment(tx, {"FOREIGN_COUNTRY", "IMPOSSIBLE_TRAVEL"})


def test_unusual_amount_compared_to_habits(customer, account):
    for _ in range(3):
        customer.transact(account["id"], "DEPOSIT", "100.00")

    tx = customer.transact(account["id"], "DEPOSIT", "501.00").json()

    assert_assessment(tx, {"UNUSUAL_AMOUNT"})


def test_exactly_five_times_the_average_is_not_unusual(customer, account):
    for _ in range(3):
        customer.transact(account["id"], "DEPOSIT", "100.00")

    tx = customer.transact(account["id"], "DEPOSIT", "500.00").json()

    assert_assessment(tx, set())


def test_velocity_on_the_sixth_quick_transaction(customer, account):
    for _ in range(5):
        customer.transact(account["id"], "DEPOSIT", "10.00")

    tx = customer.transact(account["id"], "DEPOSIT", "10.00").json()

    assert "VELOCITY" in {r["code"] for r in tx["triggeredRules"]}


def test_blocked_transaction_does_not_move_money(customer, account):
    customer.transact(account["id"], "DEPOSIT", "20000.00")  # large amount: flagged, but money moves

    tx = customer.transact(account["id"], "WITHDRAWAL", "15000.00", country="US").json()

    assert_assessment(tx, {"LARGE_AMOUNT", "FOREIGN_COUNTRY", "IMPOSSIBLE_TRAVEL"})
    assert tx["status"] == "BLOCKED"
    assert Decimal(str(customer.account(account["id"])["balance"])) == Decimal("20000.00")


def test_every_rule_explains_itself(customer, funded_account):
    tx = customer.transact(funded_account["id"], "PAYMENT", "20.00", country="JP").json()
    for rule in tx["triggeredRules"]:
        assert rule["reason"].strip(), f"{rule['code']} has no reason"
