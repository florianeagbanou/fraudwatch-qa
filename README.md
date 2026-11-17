# FraudWatch QA

An independent, automated test suite for the [FraudWatch API](https://github.com/florianeagbanou/fraudwatch-api), written the way a QA team would test a banking system it did not build: **black-box**, through the public API and the web UI only.

> 🇫🇷 Suite de tests automatisés de l'API FraudWatch : tests d'API, de sécurité, de contrat, de bout en bout (Playwright) et de charge (Locust), avec plan de test et rapports de bogues.

![QA](https://github.com/florianeagbanou/fraudwatch-qa/actions/workflows/qa.yml/badge.svg)

## What is tested

| Suite | Tests | Examples |
|---|---|---|
| **Functional API** | accounts, transactions, money | balance exact to the cent, overdraft refused, exact balance allowed, history order |
| **Fraud rules** | every rule, at its boundaries | 9 999.99 vs 10 000, 5× vs 5×+0.01 the average, 5th vs 6th transaction |
| **Analyst workflow** | full decision table | confirmed fraud reverses a payment, false positive releases a blocked one, no double review |
| **Security** | OWASP API Top 10 | tampered JWT, `alg: none`, IDOR, role escalation, mass assignment, user enumeration, lockout, injection payloads, leaked stack traces, security headers |
| **Contract** | JSON Schema + OpenAPI | every response matches its schema, every endpoint is documented |
| **End-to-end UI** | Playwright | sign-up to deposit, flagged payment explained to the customer, analyst confirms fraud, stored XSS check |
| **Load** | Locust | 90 % customers paying, 10 % analysts polling alerts |

84 automated tests, plus 1 known defect tracked as `xfail` ([BUG-001](docs/bug-reports/BUG-001-lockout-denial-of-service.md)).

## Documentation

- [Test plan](docs/TEST_PLAN.md): scope, techniques (boundary values, decision tables, independent oracle), entry and exit criteria, risks
- [Bug reports](docs/bug-reports/): three defects found during testing, written with steps to reproduce, impact and suggested fix

## Run it locally

Start the API first (see its README), then:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

pytest tests/api                     # API, security, contract (about 5 s)
pytest -m security                   # only the security tests
pytest tests/e2e --headed --slowmo 300   # watch the browser tests
locust -f load/locustfile.py --host http://localhost:8080   # load test UI on http://localhost:8089
```

Point the suite at another environment with `BASE_URL=https://staging.example.com pytest`.

## Design choices

- **Readable tests**: `qa/client.py` wraps HTTP calls into business steps (`customer.transact(account, "PAYMENT", "50.00", country="FR")`), so each test reads like a scenario.
- **Independent oracle**: `qa/oracle.py` computes the expected rules, score and decision from the specification, not from the code under test. It adds the night-time rule when the suite runs at night, so results do not depend on the hour.
- **Isolation**: each test creates its own random user and account. No shared state, any order, safe on a shared environment.
- **Fail fast**: if the API is down, the run stops immediately with one clear message instead of 80 confusing failures.
- **Known bugs stay visible**: a confirmed defect gets a failing test marked `xfail` with its bug ID. When it is fixed, the test starts passing and `xfail_strict` makes the build fail, so the marker is removed on purpose.

## Continuous integration

`.github/workflows/qa.yml` checks out the API repository, starts it with Docker Compose (PostgreSQL + Spring Boot), waits for the health check, then runs the API tests, the browser tests and a 30-second load test. HTML reports and Playwright traces of failed tests are uploaded as build artifacts. It also runs every night as a regression check.

## Project layout

```
qa/            client, test oracle, schema validation, settings
schemas/       JSON Schemas of the API responses
tests/api/     functional, fraud, alerts, security and contract tests
tests/e2e/     Playwright browser tests
load/          Locust load test
docs/          test plan and bug reports
```

## Author

Floriane Jessica Agbanou · [LinkedIn](https://www.linkedin.com/in/florianeagbanou)
