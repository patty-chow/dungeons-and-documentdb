"""Embedding generation -- OpenAI (preferred) or Voyage AI alternative.

The provider is auto-detected from env vars:
  - OPENAI_API_KEY present -> OpenAI text-embedding-3-small (1536-dim).
    Preferred because the shipped `data/srd_spells_embedded.json` is
    generated with this model. Using a different provider at query
    time would produce vectors of incompatible dimensions and the
    cosmosSearch index would reject the query.
  - VOYAGE_API_KEY present -> Voyage AI. Use this only if you also
    re-embed the spell book with `python scripts/seed_all.py` so the
    index matches.

We keep this module deliberately tiny so beginners can read and adapt it.
"""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@lru_cache(maxsize=1)
def _provider() -> str:
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("VOYAGE_API_KEY"):
        return "voyage"
    raise RuntimeError(
        "No embeddings provider configured. Set OPENAI_API_KEY (preferred, "
        "matches the shipped embedded data) or VOYAGE_API_KEY in your .env file."
    )


def provider_name() -> str:
    """Friendly name of the configured embeddings provider."""
    return _provider()


def embed(text: str) -> list[float]:
    """Embed a single string. Returns a vector (list of floats)."""
    return embed_batch([text])[0]


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a list of strings. Returns a list of vectors."""
    if _provider() == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        resp = client.embeddings.create(model=model, input=texts)
        return [list(map(float, item.embedding)) for item in resp.data]

    # Voyage AI alternative
    import voyageai

    client = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
    model = os.getenv("VOYAGE_MODEL", "voyage-3-lite")
    result = client.embed(texts, model=model, input_type="document")
    return [list(map(float, e)) for e in result.embeddings]


@lru_cache(maxsize=1)
def dimensions() -> int:
    """Return the embedding dimension by sampling a single short string.

    We call the embedding API once and measure. This is robust against the
    provider changing default dimensions across model releases.
    """
    return len(embed("dimensions"))
