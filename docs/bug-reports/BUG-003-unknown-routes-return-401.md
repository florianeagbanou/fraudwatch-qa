# BUG-003: Unknown routes return 401/403 instead of 404

| Field | Value |
|---|---|
| Severity | Low |
| Priority | Low |
| Component | Security configuration |
| Type | Usability / API design |
| Found by | Exploratory testing |

## Summary
Because the security configuration denies every route that is not explicitly allowed, a typo in a URL (e.g. `/api/acounts`) returns `401 Unauthorized` without a token, or `403 Forbidden` with one, instead of `404 Not Found`.

## Steps to reproduce
1. Log in as a customer.
2. Call `GET /api/acounts` (typo).

## Expected result
`404 Not Found`.

## Actual result
`403 Forbidden`.

## Note
Deny-by-default is a good security practice and hides the API surface from attackers, so this may be accepted as a design choice. Logged so the team can decide, and to document the behaviour for client developers.
