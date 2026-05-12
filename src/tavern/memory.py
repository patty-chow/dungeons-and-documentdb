"""Conversation memory storage + retrieval (the heart of Demo 1)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo.database import Database


def get_recent_conversations(
    db: Database,
    player_id: str,
    npc_id: str,
    limit: int = 5,
) -> list[dict]:
    """Return the player's most recent N conversation turns with this NPC.

    Results are returned oldest-first so the LLM reads them naturally.
    """
    cursor = (
        db.conversations
        .find({"player_id": player_id, "npc_id": npc_id})
        .sort("timestamp", -1)
        .limit(limit)
    )
    return list(reversed(list(cursor)))


def save_conversation(
    db: Database,
    *,
    player_id: str,
    npc_id: str,
    npc_name: str,
    player_message: str,
    npc_response: str,
    topics: list[str] | None = None,
    quests: list[str] | None = None,
    mood: str | None = None,
) -> Any:
    """Append a single conversation turn to the conversations collection."""
    doc = {
        "player_id": player_id,
        "npc_id": npc_id,
        "npc_name": npc_name,
        "timestamp": datetime.now(timezone.utc),
        "player_message": player_message,
        "npc_response": npc_response,
        "topics_mentioned": topics or [],
        "quest_refs": quests or [],
        "mood": mood or "neutral",
    }
    return db.conversations.insert_one(doc).inserted_id


def extract_topics(text: str) -> list[str]:
    """Naive topic extraction: lowercase keyword spotting.

    For the demo we keep this simple. A production agent would use the LLM
    (or a smaller model) to extract structured entities.
    """
    keywords = [
        "goblin", "goblins", "dragon", "dragons", "bandit", "bandits",
        "whisperwood", "mayor", "bounty", "quest", "tavern", "potion",
        "gold", "sword", "wizard", "elf", "dwarf", "orc", "orcs",
    ]
    lower = text.lower()
    found: list[str] = []
    for kw in keywords:
        if kw in lower and kw not in found:
            found.append(kw)
    return found
