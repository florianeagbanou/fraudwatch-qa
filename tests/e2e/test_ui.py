"""Browser tests of the demo web interface, with Playwright.

Run headed to watch them:  pytest tests/e2e --headed --slowmo 300
"""

import re

import pytest
from playwright.sync_api import Page, expect

from qa.client import unique_username
from qa.config import ANALYST, BASE_URL, DEFAULT_PASSWORD
from qa.oracle import is_night

pytestmark = pytest.mark.e2e


def sign_up(page: Page) -> str:
    username = unique_username("ui")
    page.goto(BASE_URL)
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(DEFAULT_PASSWORD)
    page.get_by_role("button", name="Create account").click()
    expect(page.get_by_test_id("session-user")).to_have_text(f"{username} (USER)")
    return username


def open_account(page: Page) -> None:
    """Click "Open account" and wait until the account is shown, so the next action has an account to use."""
    page.get_by_role("button", name="Open account").click()
    expect(page.get_by_test_id("account")).to_have_count(1)


def send(page: Page, type_: str, amount: str, country: str = "CA") -> None:
    page.get_by_label("Type").select_option(type_)
    page.get_by_label("Amount").fill(amount)
    page.get_by_label("Country", exact=True).fill(country)
    page.get_by_role("button", name="Send").click()


def test_wrong_password_shows_an_error(page: Page):
    page.goto(BASE_URL)
    page.get_by_label("Username").fill(unique_username())
    page.get_by_label("Password").fill("WrongPass1")
    page.get_by_role("button", name="Log in").click()
    expect(page.get_by_test_id("message")).to_have_text("Invalid username or password")


def test_customer_opens_account_and_deposits(page: Page):
    sign_up(page)

    open_account(page)

    send(page, "DEPOSIT", "250")

    expect(page.get_by_test_id("tx-result")).to_contain_text("APPROVED")
    expect(page.get_by_test_id("account")).to_contain_text("250.00 CAD")
    expect(page.get_by_test_id("tx-history").locator("tr")).to_have_count(1)


def test_suspicious_payment_is_explained_to_the_customer(page: Page):
    sign_up(page)
    open_account(page)
    send(page, "DEPOSIT", "1000")
    expect(page.get_by_test_id("tx-result")).to_contain_text("APPROVED")

    send(page, "PAYMENT", "50", country="FR")

    result = page.get_by_test_id("tx-result")
    expect(result).to_contain_text("BLOCKED" if is_night() else "FLAGGED")
    expect(result).to_contain_text("IMPOSSIBLE_TRAVEL")
    expect(result).to_contain_text("FOREIGN_COUNTRY")


def test_insufficient_funds_message(page: Page):
    sign_up(page)
    open_account(page)

    send(page, "PAYMENT", "10")

    expect(page.get_by_test_id("message")).to_have_text("Insufficient funds")


def test_analyst_confirms_fraud_from_the_dashboard(page: Page):
    # A customer makes a suspicious payment...
    sign_up(page)
    open_account(page)
    send(page, "DEPOSIT", "20000")
    send(page, "WITHDRAWAL", "15000", country="US")
    expect(page.get_by_test_id("tx-result")).to_contain_text("BLOCKED")
    account_number = re.search(r"FW-\d{10}", page.get_by_test_id("account").inner_text()).group(0)
    page.get_by_role("button", name="Log out").click()

    # ...and the analyst reviews it
    page.get_by_label("Username").fill(ANALYST[0])
    page.get_by_label("Password").fill(ANALYST[1])
    page.get_by_role("button", name="Log in").click()
    row = page.get_by_test_id("alert-row").filter(has_text=account_number).filter(has_text="15,000.00")
    expect(row).to_have_count(1)

    row.get_by_role("button", name="Confirm fraud").click()

    expect(page.get_by_test_id("message")).to_contain_text("CONFIRMED_FRAUD")
    expect(page.get_by_test_id("alert-row").filter(has_text=account_number).filter(has_text="15,000.00")).to_have_count(0)


def test_api_values_are_displayed_as_text_not_html(page: Page):
    """Stored XSS check: a merchant name with HTML must not create elements in the page."""
    sign_up(page)
    open_account(page)
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))

    page.get_by_label("Merchant").fill("<img src=x onerror=alert(1)>")
    send(page, "DEPOSIT", "5")

    expect(page.get_by_test_id("tx-result")).to_contain_text("APPROVED")
    assert page.locator("img[src=x]").count() == 0
    assert dialogs == []
