"""Tests for tavern.memory and tavern.player.

Uses live DocumentDB (it's local in Docker). Cleans up after itself.
"""
from __future__ import annotations

import pytest

from src.db import get_db, ping
from src.tavern.memory import (
    extract_topics, get_recent_conversations, save_conversation,
)
from src.tavern.player import get_or_create_player, learn_quest, record_visit

PLAYER_ID = "_test_player"
NPC_ID = "_test_npc"


@pytest.fixture(scope="function")
def db():
    if not ping():
        pytest.skip(
            "DocumentDB not reachable -- run `docker compose up -d` first."
        )
    d = get_db()
    # Pre-clean (in case a previous run was interrupted).
    d.conversations.delete_many({"player_id": PLAYER_ID})
    d.players.delete_many({"_id": PLAYER_ID})
    yield d
    # Post-clean.
    d.conversations.delete_many({"player_id": PLAYER_ID})
    d.players.delete_many({"_id": PLAYER_ID})


def test_extract_topics():
    text = "I want to fight goblins in the Whisperwood for a bounty"
    topics = extract_topics(text)
    assert "goblins" in topics
    assert "whisperwood" in topics
    assert "bounty" in topics


def test_get_or_create_player_is_idempotent(db):
    p1 = get_or_create_player(db, PLAYER_ID, name="Test")
    assert p1["visit_count"] == 0
    p2 = get_or_create_player(db, PLAYER_ID)
    assert p2["_id"] == p1["_id"]
    # Did not duplicate.
    assert db.players.count_documents({"_id": PLAYER_ID}) == 1


def test_record_visit_increments(db):
    get_or_create_player(db, PLAYER_ID)
    record_visit(db, PLAYER_ID)
    record_visit(db, PLAYER_ID)
    p = db.players.find_one({"_id": PLAYER_ID})
    assert p is not None
    assert p["visit_count"] == 2


def test_learn_quest_no_duplicates(db):
    get_or_create_player(db, PLAYER_ID)
    learn_quest(db, PLAYER_ID, "goblin_clearing")
    learn_quest(db, PLAYER_ID, "goblin_clearing")
    p = db.players.find_one({"_id": PLAYER_ID})
    assert p["known_quests"].count("goblin_clearing") == 1


def test_save_and_retrieve_conversation(db):
    save_conversation(
        db,
        player_id=PLAYER_ID, npc_id=NPC_ID, npc_name="Test",
        player_message="Hello", npc_response="Greetings",
        topics=["greeting"],
    )
    save_conversation(
        db,
        player_id=PLAYER_ID, npc_id=NPC_ID, npc_name="Test",
        player_message="Goodbye", npc_response="Farewell",
    )
    history = get_recent_conversations(db, PLAYER_ID, NPC_ID, limit=5)
    assert len(history) == 2
    # Oldest first (so the LLM reads chronologically).
    assert history[0]["player_message"] == "Hello"
    assert history[1]["player_message"] == "Goodbye"
