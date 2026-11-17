"""Load test: simulated customers making transactions while analysts poll the alert queue.

Run with a web UI:     locust -f load/locustfile.py --host http://localhost:8080
Run headless (CI):     locust -f load/locustfile.py --host http://localhost:8080 --headless -u 20 -r 5 -t 30s
"""

import random
import uuid

from locust import HttpUser, between, task

COUNTRIES = ["CA"] * 8 + ["US", "FR"]  # mostly at home, sometimes abroad


class Customer(HttpUser):
    weight = 9
    wait_time = between(0.5, 2)

    def on_start(self):
        username = f"load_{uuid.uuid4().hex[:10]}"
        self.client.post("/api/auth/register", json={"username": username, "password": "Password123"})
        token = self.client.post("/api/auth/login", json={"username": username, "password": "Password123"}).json()
        self.client.headers["Authorization"] = f"Bearer {token['accessToken']}"
        account = self.client.post("/api/accounts", json={"homeCountry": "CA", "currency": "CAD"}).json()
        self.account_id = account["id"]
        self.client.post(
            f"/api/accounts/{self.account_id}/transactions",
            json={"type": "DEPOSIT", "amount": "5000", "country": "CA"},
            name="/api/accounts/[id]/transactions",
        )

    @task(5)
    def pay(self):
        self.client.post(
            f"/api/accounts/{self.account_id}/transactions",
            json={"type": "PAYMENT", "amount": str(random.randint(1, 80)), "country": random.choice(COUNTRIES)},
            name="/api/accounts/[id]/transactions",
        )

    @task(2)
    def history(self):
        self.client.get(f"/api/accounts/{self.account_id}/transactions", name="/api/accounts/[id]/transactions")

    @task(1)
    def accounts(self):
        self.client.get("/api/accounts")


class Analyst(HttpUser):
    weight = 1
    wait_time = between(2, 5)

    def on_start(self):
        token = self.client.post("/api/auth/login", json={"username": "analyst", "password": "Analyst123!"}).json()
        self.client.headers["Authorization"] = f"Bearer {token['accessToken']}"

    @task
    def open_alerts(self):
        self.client.get("/api/alerts?status=OPEN", name="/api/alerts")
