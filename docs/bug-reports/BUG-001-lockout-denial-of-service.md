# BUG-001: Anyone can lock any customer out of their account

| Field | Value |
|---|---|
| Severity | Medium |
| Priority | High |
| Component | Authentication (`POST /api/auth/login`) |
| Type | Security, denial of service |
| Found by | Exploratory testing, automated in `test_third_party_cannot_lock_out_a_customer` (xfail) |

## Summary
The brute-force protection locks a **username** after 5 failed logins, whoever sends them. An attacker who knows (or guesses) a customer's username can lock that customer out for 15 minutes, again and again, without knowing any password.

## Steps to reproduce
1. Register a customer `victim` with password `Password123`.
2. From any other client, send 5 login requests for `victim` with a wrong password.
3. Log in as `victim` with the correct password.

## Expected result
The real customer can still log in, or is asked for an extra verification step.

## Actual result
`423 Locked` with `Retry-After: 900`. The customer cannot log in for 15 minutes.

## Impact
An attacker can block many customers by cycling through usernames, for example during a payment deadline.

## Suggested fix
Combine the lock with the client IP (lock *username + IP* rather than username alone), add progressive delays or a CAPTCHA instead of a hard lock, and alert the customer by email.
