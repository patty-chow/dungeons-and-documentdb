"""Auto-load data into DocumentDB without needing any LLM API key.

Runs as part of the codespace post-create step. Loads:
  - NPCs (Bram the tavern keeper)
  - The demo player document
  - Spells, with embeddings if `data/srd_spells_embedded.json` exists
    (preferred), otherwise raw spell metadata only

If embedded data is present, the cosmosSearch vector index is also created
so the spell-book demo's vector search works immediately. If only raw data
is loaded, the spell collection still browses cleanly in the DocumentDB
extension and the user can run `python scripts/seed_all.py` later (with
their own LLM key) to add embeddings.

Idempotent: safe to re-run. Existing docs are replaced/upserted.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from rich.console import Console  # noqa: E402

from scripts.setup_db import (  # noqa: E402
    VECTOR_INDEX_NAME,
    ensure_basic_indexes,
    ensure_collections,
)
from src.db import get_db, ping  # noqa: E402
from src.tavern.npc import BRAM_DEFAULT  # noqa: E402

console = Console()

DEMO_PLAYER_ID = "adventurer_001"
EMBEDDED_PATH = _PROJECT_ROOT / "data" / "srd_spells_embedded.json"
RAW_PATH = _PROJECT_ROOT / "data" / "srd_spells.json"


def seed_npcs() -> None:
    db = get_db()
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


def load_embedded_spells() -> int:
    """Load pre-embedded spells and create the vector index. No LLM needed."""
    db = get_db()
    payload = json.loads(EMBEDDED_PATH.read_text(encoding="utf-8"))
    spells = payload["spells"]
    meta = payload.get("_metadata", {})
    dims = int(meta.get("dimensions") or len(spells[0]["embedding"]))

    db.spells.delete_many({})
    db.spells.insert_many(spells)
    console.print(
        f"  ✓  Inserted [bold]{len(spells)}[/bold] spells "
        f"(pre-embedded, {dims}-dim, provider={meta.get('embedding_provider', '?')})"
    )

    # Create the cosmosSearch index now that we know the dimensions.
    existing = {idx["name"] for idx in db.spells.list_indexes()}
    if VECTOR_INDEX_NAME in existing:
        db.spells.drop_index(VECTOR_INDEX_NAME)
    db.command({
        "createIndexes": "spells",
        "indexes": [{
            "name": VECTOR_INDEX_NAME,
            "key": {"embedding": "cosmosSearch"},
            "cosmosSearchOptions": {
                "kind": "vector-hnsw",
                "dimensions": dims,
                "similarity": "COS",
                "m": 16,
                "efConstruction": 64,
            },
        }],
    })
    console.print(f"  🪄 Vector index created ({dims} dims, HNSW, cosine).")
    return len(spells)


def load_raw_spells() -> int:
    """Fallback: load spells WITHOUT embeddings. Vector search disabled."""
    db = get_db()
    spells = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    db.spells.delete_many({})
    db.spells.insert_many(spells)
    console.print(
        f"  ⚠  Inserted [bold]{len(spells)}[/bold] spells WITHOUT embeddings."
    )
    console.print(
        "     [yellow]Vector search will not work until you run "
        "`python scripts/seed_all.py` with an LLM key set in .env.[/yellow]"
    )
    return len(spells)


def main() -> None:
    console.rule("[bold]🐉 Loading sample data into DocumentDB[/bold]")
    if not ping():
        console.print(
            "[red]❌ Could not reach DocumentDB.[/red]\n"
            "[dim]Is the documentdb service up? "
            "Try `docker compose up -d documentdb`.[/dim]"
        )
        sys.exit(1)

    ensure_collections()
    ensure_basic_indexes()
    seed_npcs()
    seed_demo_player()

    if EMBEDDED_PATH.exists():
        load_embedded_spells()
        mode = "[green]full[/green] (vector search ready)"
    else:
        load_raw_spells()
        mode = "[yellow]basic[/yellow] (no vector search yet)"

    console.rule(f"[bold]Data load complete -- mode: {mode}[/bold]")


if __name__ == "__main__":
    main()
