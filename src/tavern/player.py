"""Player state management for the tavern demo."""
from __future__ import annotations

from datetime import datetime, timezone

from pymongo.database import Database


def get_or_create_player(
    db: Database,
    player_id: str,
    name: str | None = None,
) -> dict:
    """Fetch the player document, creating a fresh one if it does not exist."""
    existing = db.players.find_one({"_id": player_id})
    if existing:
        return existing

    fresh = {
        "_id": player_id,
        "name": name or "Adventurer",
        "visit_count": 0,
        "known_quests": [],
        "reputation": "neutral",
        "last_visit": None,
    }
    db.players.insert_one(fresh)
    return fresh


def record_visit(db: Database, player_id: str) -> None:
    """Increment visit_count and stamp last_visit."""
    db.players.update_one(
        {"_id": player_id},
        {
            "$inc": {"visit_count": 1},
            "$set": {"last_visit": datetime.now(timezone.utc)},
        },
    )


def learn_quest(db: Database, player_id: str, quest_id: str) -> None:
    """Add a quest reference to the player's known_quests (no duplicates)."""
    db.players.update_one(
        {"_id": player_id},
        {"$addToSet": {"known_quests": quest_id}},
    )
