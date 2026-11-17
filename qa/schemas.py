"""Contract checks: the response body must match a JSON schema, not just "contain some fields"."""

import json
from functools import cache
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


@cache
def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((SCHEMA_DIR / f"{name}.json").read_text()))


def assert_matches(name: str, payload) -> None:
    errors = sorted(_validator(name).iter_errors(payload), key=lambda e: list(e.path))
    assert not errors, f"{name} schema violations:\n" + "\n".join(f"  {list(e.path)}: {e.message}" for e in errors)
