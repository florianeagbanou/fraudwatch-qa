# BUG-002: Transaction history is not paginated

| Field | Value |
|---|---|
| Severity | Low |
| Priority | Medium |
| Component | `GET /api/accounts/{id}/transactions` |
| Type | Performance |
| Found by | Load test review |

## Summary
The endpoint returns every transaction of the account in one response. The response grows without limit with the age of the account.

## Steps to reproduce
1. Create an account and 1 000 transactions (spaced out to avoid the velocity rule).
2. Call `GET /api/accounts/{id}/transactions`.

## Expected result
A page of results (for example 50) with a way to request the next page.

## Actual result
All 1 000 transactions in a single response. Response time and size grow linearly.

## Suggested fix
Add `page` and `size` parameters (Spring Data `Pageable`) with a maximum page size, and return paging metadata.
