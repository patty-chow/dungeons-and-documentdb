"""End-to-end seed: collections, indexes, NPCs, demo player, and spells.

Run once after `docker compose up -d`:
    python scripts/seed_all.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Make `from src...` and `from scripts...` work when invoked directly.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from rich.console import Console  # noqa: E402

from scripts.setup_db import (  # noqa: E402
    ensure_basic_indexes, ensure_collections, ensure_vector_index,
)
from src.db import get_db, ping  # noqa: E402
from src.spellbook.seed import seed_spells  # noqa: E402
from src.tavern.npc import BRAM_DEFAULT  # noqa: E402

console = Console()

DEMO_PLAYER_ID = "adventurer_001"


def seed_npcs() -> None:
    db = get_db()
    # `replace_one` with upsert handles both insert and update cleanly and
    # avoids the "_id is immutable" error you'd get from `$set` with _id.
    db.npcs.replace_one(
        {"_id": BRAM_DEFAULT["_id"]},
        BRAM_DEFAULT,
        upsert=True,
    )
    console.print(f"  ✓  NPC seeded: [bold]{BRAM_DEFAULT['name']}[/bold]")


def seed_demo_player() -> None:
    db = get_db()
    db.players.update_one(
        {"_id": DEMO_PLAYER_ID},
        {
            "$setOnInsert": {
                "_id": DEMO_PLAYER_ID,
                "name": "Adventurer",
                "visit_count": 0,
                "known_quests": [],
                "reputation": "neutral",
                "last_visit": None,
                "created_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
    console.print(f"  ✓  Player seeded: [bold]{DEMO_PLAYER_ID}[/bold]")


def main() -> None:
    console.rule("[bold]🐉 Dungeons and DocumentDB -- Seeding the realm[/bold]")
    if not ping():
        console.print(
            "[red]❌ Could not reach DocumentDB.[/red]\n"
            "[dim]Run `docker compose up -d` and try again. "
            "First boot takes ~10 seconds.[/dim]"
        )
        sys.exit(1)

    ensure_collections()
    ensure_basic_indexes()
    seed_npcs()
    seed_demo_player()
    seed_spells()
    # The vector index needs to exist AFTER we know the embedding
    # dimensions (we discover them by sampling one embedding).
    ensure_vector_index()
    console.rule("[bold green]✨ Realm ready[/bold green]")
    console.print()
    console.print("Run the demos:")
    console.print(
        "  [bold]python -m src.tavern.chat[/bold]    -- talk to Bram"
    )
    console.print(
        "  [bold]python -m src.spellbook.chat[/bold] -- ask Elara about spells"
    )


if __name__ == "__main__":
    main()
