# Test plan: FraudWatch API

| | |
|---|---|
| **Product** | FraudWatch API 1.0.0 ([repository](https://github.com/florianeagbanou/fraudwatch-api)) |
| **Author** | Floriane Jessica Agbanou |
| **Approach** | Black-box: the suite only uses the public HTTP API and the web UI, never the source code |

## 1. Objectives

1. Confirm that money moves correctly (no lost or duplicated cents, no overdraft).
2. Confirm that each fraud rule triggers when it should and **only** when it should.
3. Confirm the analyst workflow: alerts are opened, reviewed once, and the money follows the decision.
4. Find security weaknesses in authentication and authorization (OWASP API Security Top 10).
5. Measure response times under a realistic load.

## 2. Scope

| In scope | Out of scope |
|---|---|
| REST API: auth, accounts, transactions, alerts, audit | Database internals |
| Demo web UI (main user journeys) | Visual design, browser compatibility beyond Chromium |
| Fraud rules and thresholds | Tuning of thresholds (business decision) |
| Load: 20 concurrent users | Stress and endurance tests |

## 3. Test levels and tools

| Level | Tool | Folder |
|---|---|---|
| API functional | pytest + requests | `tests/api/` |
| Contract | JSON Schema, OpenAPI | `schemas/`, `tests/api/test_contract.py` |
| Security | pytest (manual attack scenarios automated) | `tests/api/test_security.py` |
| End-to-end UI | Playwright | `tests/e2e/` |
| Load | Locust | `load/locustfile.py` |

## 4. Test design techniques

- **Boundary value analysis**: amounts at 9 999.99 / 10 000 (large amount), 5× vs 5×+1 the average (unusual amount), 5th vs 6th transaction (velocity), 100.00 vs 100.01 with a 100.00 balance (insufficient funds), passwords of 7/8/72/73+ characters.
- **Equivalence partitioning**: valid / invalid country codes, transaction types, roles.
- **Decision table** for alert reviews:

  | Transaction | Resolution | Expected transaction status | Expected money |
  |---|---|---|---|
  | FLAGGED | FALSE_POSITIVE | APPROVED | unchanged (already moved) |
  | FLAGGED | CONFIRMED_FRAUD | BLOCKED | reversed |
  | BLOCKED | FALSE_POSITIVE | APPROVED | moves now |
  | BLOCKED | CONFIRMED_FRAUD | BLOCKED | unchanged |

- **Test oracle independent from the code** (`qa/oracle.py`): expected rules and score are computed from the specification. It also accounts for the time-dependent night rule, so results are the same at noon or at 2 a.m.
- **Negative and abuse cases**: tampered and unsigned JWTs, IDOR, role escalation, mass assignment, injection payloads, stored XSS in the UI.

## 5. Test data

Every test creates its own user and account with a random name. Tests never depend on each other or on execution order, and can run against a shared environment.

## 6. Entry and exit criteria

- **Entry**: `/actuator/health` returns `UP` (checked automatically before the run).
- **Exit**: all tests pass except known, documented defects (marked `xfail` with their bug ID); no open defect of severity High or Critical; load test with 0 % errors and p95 under 500 ms.

## 7. Risks

| Risk | Mitigation |
|---|---|
| Time-dependent rules make results vary | Oracle adds the night rule when needed; tests that need a specific outcome skip at night |
| Tests share a database | Unique users and accounts per test |
| Demo analyst account gets locked by failed-login tests | Failed logins on `analyst` are limited to one per run; any successful login resets the counter |

## 8. Defects found

See [`bug-reports/`](bug-reports/).

| ID | Title | Severity | Status |
|---|---|---|---|
| [BUG-001](bug-reports/BUG-001-lockout-denial-of-service.md) | Anyone can lock any customer out of their account | Medium | Open, covered by an `xfail` test |
| [BUG-002](bug-reports/BUG-002-history-not-paginated.md) | Transaction history is not paginated | Low | Open |
| [BUG-003](bug-reports/BUG-003-unknown-routes-return-401.md) | Unknown routes return 401/403 instead of 404 | Low | Open (by design, to be discussed) |
