"""Vector + hybrid search over the `spells` collection.

The magic happens in three lines: embed the query, ship it to the
`$search` aggregation stage with the `cosmosSearch` operator, project the
fields you care about.
"""
from __future__ import annotations

from pymongo.database import Database

from src.embeddings import embed

PROJECTION = {
    "name": 1, "level": 1, "school": 1, "casting_time": 1, "range": 1,
    "components": 1, "duration": 1, "concentration": 1, "description": 1,
    "damage_type": 1, "classes": 1, "tags": 1,
    "score": {"$meta": "searchScore"},
}


def search_spells(
    db: Database,
    query: str,
    filters: dict | None = None,
    k: int = 5,
) -> list[dict]:
    """Return up to *k* spells semantically similar to *query*.

    Parameters
    ----------
    db
        Active DocumentDB Database handle.
    query
        Natural-language question (e.g. ``"fire damage area attack"``).
    filters
        Optional MongoDB filter applied *after* the vector stage, e.g.
        ``{"concentration": False, "level": {"$lte": 3}}``.
    k
        How many spells the vector index should return.
    """
    vector = embed(query)
    pipeline: list[dict] = [
        {
            "$search": {
                "cosmosSearch": {
                    "vector": vector,
                    "path": "embedding",
                    "k": k,
                }
            }
        },
        {"$project": PROJECTION},
    ]
    if filters:
        pipeline.append({"$match": filters})
    return list(db.spells.aggregate(pipeline))
