"""Test oracle: what the API *should* answer, computed independently from the implementation.

The night rule depends on the real time in Montreal, so a test that hard-codes "score = 60"
would fail if run at 2 a.m. The oracle adds the night bonus when needed, so the suite is
deterministic whatever the hour.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

POINTS = {
    "LARGE_AMOUNT": 40,
    "UNUSUAL_AMOUNT": 30,
    "VELOCITY": 35,
    "FOREIGN_COUNTRY": 15,
    "IMPOSSIBLE_TRAVEL": 45,
    "NIGHT_ACTIVITY": 10,
}
FLAG_THRESHOLD = 40
BLOCK_THRESHOLD = 70
MONTREAL = ZoneInfo("America/Toronto")


def is_night(now: datetime | None = None) -> bool:
    hour = (now or datetime.now(MONTREAL)).astimezone(MONTREAL).hour
    return 0 <= hour < 5


def expected(rules: set[str]) -> tuple[set[str], int, str]:
    """Rules, score and status the API should return, given the non-time rules we triggered."""
    rules = set(rules)
    if is_night():
        rules.add("NIGHT_ACTIVITY")
    score = min(100, sum(POINTS[r] for r in rules))
    if score >= BLOCK_THRESHOLD:
        status = "BLOCKED"
    elif score >= FLAG_THRESHOLD:
        status = "FLAGGED"
    else:
        status = "APPROVED"
    return rules, score, status


def assert_assessment(transaction: dict, rules: set[str]) -> None:
    expected_rules, expected_score, expected_status = expected(rules)
    actual_rules = {r["code"] for r in transaction["triggeredRules"]}
    assert actual_rules == expected_rules, f"rules {actual_rules} != {expected_rules}"
    assert transaction["riskScore"] == expected_score
    assert transaction["status"] == expected_status
