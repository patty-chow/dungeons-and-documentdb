"""Tests for the DocumentDB connection helpers.

These are integration tests -- they require DocumentDB to be running. If it
is not, the tests skip with a friendly message instead of failing.
"""
from __future__ import annotations

import pytest

from src.db import get_client, get_db, ping


@pytest.fixture(scope="module")
def db():
    if not ping():
        pytest.skip(
            "DocumentDB not reachable -- run `docker compose up -d` first."
        )
    return get_db()


def test_ping_does_not_raise():
    # Smoke test: ping() always returns a bool, never raises.
    assert isinstance(ping(), bool)


def test_client_is_cached():
    assert get_client() is get_client()


def test_db_round_trip(db):
    """Insert, read, delete -- the simplest possible round trip."""
    doc = {"_id": "test_round_trip", "msg": "huzzah"}
    db.test_round_trip.delete_one({"_id": doc["_id"]})
    db.test_round_trip.insert_one(doc)
    fetched = db.test_round_trip.find_one({"_id": doc["_id"]})
    assert fetched is not None
    assert fetched["msg"] == "huzzah"
    db.test_round_trip.delete_one({"_id": doc["_id"]})
