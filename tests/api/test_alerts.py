"""The analyst workflow: alerts are opened, reviewed, and money follows the decision."""

from decimal import Decimal

import pytest

from qa.oracle import is_night


def balance(client, account_id) -> Decimal:
    return Decimal(str(client.account(account_id)["balance"]))


@pytest.fixture
def flagged(customer, funded_account):
    """A 50 $ payment in France right after a deposit in Canada: flagged (or blocked at night)."""
    if is_night():
        pytest.skip("At night this payment is BLOCKED, not FLAGGED (night rule adds 10 points)")
    tx = customer.transact(funded_account["id"], "PAYMENT", "50.00", country="FR").json()
    assert tx["status"] == "FLAGGED"
    return tx


def test_flagged_transaction_opens_an_alert(analyst, flagged):
    alert = analyst.alert_for(flagged["id"])
    assert alert["status"] == "OPEN"
    assert alert["amount"] == 50.0
    assert {r["code"] for r in alert["triggeredRules"]} == {"FOREIGN_COUNTRY", "IMPOSSIBLE_TRAVEL"}


def test_approved_transaction_opens_no_alert(analyst, customer, account):
    tx = customer.transact(account["id"], "DEPOSIT", "10.00").json()
    assert all(a["transactionId"] != tx["id"] for a in analyst.alerts(status=None))


def test_confirmed_fraud_gives_the_money_back(analyst, customer, funded_account, flagged):
    assert balance(customer, funded_account["id"]) == Decimal("950.00")

    response = analyst.review(analyst.alert_for(flagged["id"])["id"], "CONFIRMED_FRAUD")

    assert response.status_code == 200
    assert response.json()["transactionStatus"] == "BLOCKED"
    assert balance(customer, funded_account["id"]) == Decimal("1000.00")


def test_false_positive_releases_a_blocked_transaction(analyst, customer, account):
    customer.transact(account["id"], "DEPOSIT", "20000.00")
    blocked = customer.transact(account["id"], "WITHDRAWAL", "15000.00", country="US").json()
    assert blocked["status"] == "BLOCKED"

    response = analyst.review(analyst.alert_for(blocked["id"])["id"], "FALSE_POSITIVE")

    assert response.status_code == 200
    assert response.json()["transactionStatus"] == "APPROVED"
    assert balance(customer, account["id"]) == Decimal("5000.00")


def test_alert_cannot_be_reviewed_twice(analyst, flagged):
    alert_id = analyst.alert_for(flagged["id"])["id"]
    assert analyst.review(alert_id, "FALSE_POSITIVE").status_code == 200

    assert analyst.review(alert_id, "CONFIRMED_FRAUD").status_code == 409


def test_review_records_who_and_when(analyst, flagged):
    alert_id = analyst.alert_for(flagged["id"])["id"]
    reviewed = analyst.review(alert_id, "FALSE_POSITIVE", note="Customer confirmed by phone").json()

    assert reviewed["reviewedBy"] == "analyst"
    assert reviewed["reviewedAt"]
    assert reviewed["resolutionNote"] == "Customer confirmed by phone"


def test_reopening_an_alert_is_not_a_valid_resolution(analyst, flagged):
    alert_id = analyst.alert_for(flagged["id"])["id"]
    assert analyst.review(alert_id, "OPEN").status_code == 422


def test_unknown_alert(analyst):
    assert analyst.review(999_999_999, "FALSE_POSITIVE").status_code == 404


def test_filter_by_status(analyst, flagged):
    open_ids = [a["id"] for a in analyst.alerts("OPEN")]
    alert_id = analyst.alert_for(flagged["id"])["id"]
    assert alert_id in open_ids

    analyst.review(alert_id, "FALSE_POSITIVE")

    assert alert_id not in [a["id"] for a in analyst.alerts("OPEN")]
    assert alert_id in [a["id"] for a in analyst.alerts("FALSE_POSITIVE")]
