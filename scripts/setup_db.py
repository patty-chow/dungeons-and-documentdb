"""Create collections + indexes (regular + cosmosSearch vector).

Idempotent: safe to re-run. The vector index is dropped and recreated so
that its dimensions always match the configured embedding model.

Run from the project root:
    python scripts/setup_db.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `from src...` work when this is run as `python scripts/setup_db.py`.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from rich.console import Console  # noqa: E402

from src.db import get_db  # noqa: E402
from src.embeddings import dimensions  # noqa: E402

console = Console()

COLLECTIONS = ["npcs", "players", "conversations", "spells"]
VECTOR_INDEX_NAME = "spell_vector_index"


def ensure_collections() -> None:
    """Create the four collections if they don't already exist."""
    db = get_db()
    existing = set(db.list_collection_names())
    for name in COLLECTIONS:
        if name not in existing:
            db.create_collection(name)
            console.print(f"  ➕ Created collection: [bold]{name}[/bold]")
        else:
            console.print(f"  ✓  Collection already exists: {name}")


def ensure_basic_indexes() -> None:
    """Create regular B-tree indexes that speed up the demo's queries."""
    db = get_db()
    db.conversations.create_index(
        [("player_id", 1), ("npc_id", 1), ("timestamp", -1)]
    )
    db.spells.create_index([("level", 1)])
    db.spells.create_index([("school", 1)])
    console.print("  ✓  Regular indexes ensured.")


def ensure_vector_index() -> None:
    """(Re)create the cosmosSearch vector index on `spells.embedding`."""
    db = get_db()
    dims = dimensions()
    existing = {idx["name"] for idx in db.spells.list_indexes()}

    if VECTOR_INDEX_NAME in existing:
        db.spells.drop_index(VECTOR_INDEX_NAME)
        console.print(
            f"  ♻️  Dropped existing {VECTOR_INDEX_NAME} (re-creating)."
        )

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
    console.print(
        f"  🪄 Created [bold]{VECTOR_INDEX_NAME}[/bold] "
        f"(dims={dims}, HNSW, cosine)."
    )


def main() -> None:
    console.rule("[bold]Setting up DocumentDB[/bold]")
    ensure_collections()
    ensure_basic_indexes()
    ensure_vector_index()
    console.rule("[bold green]Setup complete[/bold green]")


if __name__ == "__main__":
    main()
