"""Sign-up and login."""

import pytest

from qa.client import ApiClient, unique_username
from qa.schemas import assert_matches


@pytest.mark.smoke
def test_customer_can_sign_up_and_log_in(anonymous):
    username = unique_username()

    created = anonymous.register(username)
    assert created.status_code == 201
    assert created.json()["role"] == "USER"

    login = anonymous.login(username)
    assert login.status_code == 200
    assert_matches("token", login.json())


def test_sign_up_response_never_contains_the_password(anonymous):
    body = anonymous.register(unique_username(), "Password123").text.lower()
    assert "password" not in body
    assert "$2a$" not in body  # no BCrypt hash either


def test_duplicate_username_is_rejected(anonymous):
    username = unique_username()
    anonymous.register(username)

    response = anonymous.register(username)

    assert response.status_code == 409
    assert_matches("problem", response.json())


@pytest.mark.parametrize(
    ("password", "reason"),
    [
        ("Short1", "too short"),
        ("onlyletters", "no digit"),
        ("12345678", "no letter"),
        ("", "empty"),
        ("A1" * 40, "longer than BCrypt's 72-byte limit"),
    ],
)
def test_weak_passwords_are_rejected(anonymous, password, reason):
    response = anonymous.register(unique_username(), password)
    assert response.status_code == 400, reason
    assert "password" in response.json()["errors"]


@pytest.mark.parametrize("username", ["ab", "a" * 31, "has space", "<script>", "robert');--"])
def test_invalid_usernames_are_rejected(anonymous, username):
    response = anonymous.register(username)
    assert response.status_code == 400
    assert "username" in response.json()["errors"]


def test_role_cannot_be_chosen_at_sign_up(anonymous):
    """Mass assignment: an extra "role" field must be ignored, not make me an admin."""
    username = unique_username()
    response = anonymous.post("/api/auth/register", {"username": username, "password": "Password123", "role": "ADMIN"})
    assert response.status_code == 201
    assert response.json()["role"] == "USER"


def test_wrong_password_and_unknown_user_look_the_same(anonymous):
    """Different messages would let an attacker discover which usernames exist."""
    username = unique_username()
    anonymous.register(username)

    wrong_password = anonymous.login(username, "WrongPass1")
    unknown_user = anonymous.login(unique_username(), "WrongPass1")

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json()["detail"] == unknown_user.json()["detail"]


def test_account_is_locked_after_five_failures(anonymous):
    username = unique_username()
    anonymous.register(username)
    for _ in range(5):
        assert anonymous.login(username, "WrongPass1").status_code == 401

    locked = anonymous.login(username)  # even with the right password

    assert locked.status_code == 423
    assert int(locked.headers["Retry-After"]) > 0


def test_malformed_json_is_a_clean_400(anonymous):
    response = anonymous.post("/api/auth/login", data="{not json", headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    assert "Exception" not in response.text  # no stack trace or class names leaked


@pytest.mark.xfail(reason="BUG-001: anyone can lock any account by failing 5 logins on purpose")
def test_third_party_cannot_lock_out_a_customer(anonymous):
    victim_name = unique_username()
    victim = ApiClient()
    victim.register(victim_name)

    attacker = ApiClient()
    for _ in range(5):
        attacker.login(victim_name, "Guess12345")

    assert victim.login(victim_name).status_code == 200
