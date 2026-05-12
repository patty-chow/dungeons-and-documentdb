"""DocumentDB connection helpers.

OSS DocumentDB speaks the MongoDB wire protocol, so we use `pymongo`. The
only quirks vs MongoDB Atlas are:

  - Default port is **10260** (not 27017).
  - TLS is required, even locally, with a self-signed cert in dev.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

load_dotenv()

DEFAULT_DB_NAME = "dnd"


def _build_uri() -> str:
    """Build the MongoDB-style URI from environment variables."""
    explicit = os.getenv("DOCUMENTDB_URI", "").strip()
    if explicit:
        return explicit

    host = os.getenv("DOCUMENTDB_HOST", "localhost")
    port = os.getenv("DOCUMENTDB_PORT", "10260")
    user = os.getenv("DOCUMENTDB_USERNAME", "admin")
    pwd = os.getenv("DOCUMENTDB_PASSWORD", "dungeons123!")

    # TLS is on by default for the OSS DocumentDB image. The cert is
    # self-signed locally so we accept invalid certs in dev.
    return (
        f"mongodb://{user}:{pwd}@{host}:{port}/"
        "?tls=true&tlsAllowInvalidCertificates=true"
    )


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    """Return a cached MongoClient pointed at the local DocumentDB."""
    return MongoClient(_build_uri(), serverSelectionTimeoutMS=5000)


def get_db(client: MongoClient | None = None) -> Database:
    """Return the configured database handle (default: 'dnd')."""
    name = os.getenv("DOCUMENTDB_DATABASE", DEFAULT_DB_NAME)
    return (client or get_client())[name]


def ping() -> bool:
    """Return True if DocumentDB is reachable, False otherwise."""
    try:
        get_client().admin.command("ping")
        return True
    except Exception:
        return False
