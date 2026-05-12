"""Tests for spellbook.search.

We mock the embedding API and the database handle so this test runs without
Docker or a live DocumentDB. It asserts on the *shape* of the aggregation
pipeline that gets shipped to the database.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_search_builds_cosmos_search_pipeline():
    """The pipeline must contain cosmosSearch, projection, and filter."""
    fake_vec = [0.1] * 32
    fake_db = MagicMock()
    fake_db.spells.aggregate.return_value = iter([])

    with patch("src.spellbook.search.embed", return_value=fake_vec):
        from src.spellbook.search import search_spells
        list(search_spells(fake_db, "fire damage", filters={"level": 1}, k=3))

    fake_db.spells.aggregate.assert_called_once()
    pipeline = fake_db.spells.aggregate.call_args.args[0]

    assert pipeline[0]["$search"]["cosmosSearch"]["k"] == 3
    assert pipeline[0]["$search"]["cosmosSearch"]["path"] == "embedding"
    assert pipeline[0]["$search"]["cosmosSearch"]["vector"] == fake_vec
    # A $match stage should have been appended for the filter.
    assert any("$match" in stage for stage in pipeline)
    assert any("$project" in stage for stage in pipeline)
