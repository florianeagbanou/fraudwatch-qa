"""Where the API under test runs. Override with the BASE_URL environment variable."""

import os

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8080").rstrip("/")
ANALYST = ("analyst", "Analyst123!")
ADMIN = ("admin", "Admin123!")
DEFAULT_PASSWORD = "Password123"
