"""Seed the spells collection: load JSON, embed descriptions, insert docs."""
from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

from src.db import get_db
from src.embeddings import embed_batch

console = Console()

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "srd_spells.json"


def _embedding_input(spell: dict) -> str:
    """Build the text we embed for each spell.

    Including the name, school, tags, AND description means semantic search
    matches both topic ("undead") and mechanics ("no concentration").
    """
    return (
        f"{spell['name']} -- Level {spell['level']} {spell['school']}. "
        f"Tags: {', '.join(spell.get('tags', []))}. "
        f"{spell.get('description', '')}"
    )


def seed_spells(batch_size: int = 16) -> int:
    """Load spells from JSON, generate embeddings, replace the collection.

    Returns the number of spells inserted.
    """
    db = get_db()
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Spell data not found at {DATA_PATH}")

    spells: list[dict] = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    console.print(f"📜 Loaded [bold]{len(spells)}[/bold] spells from SRD data.")

    db.spells.delete_many({})

    with Progress() as bar:
        task = bar.add_task("Embedding spells...", total=len(spells))
        for i in range(0, len(spells), batch_size):
            chunk = spells[i:i + batch_size]
            vectors = embed_batch([_embedding_input(s) for s in chunk])
            for s, v in zip(chunk, vectors):
                s["embedding"] = v
            db.spells.insert_many(chunk)
            bar.advance(task, advance=len(chunk))

    console.print(
        f"✅ Inserted [bold]{len(spells)}[/bold] spells with embeddings."
    )
    return len(spells)


if __name__ == "__main__":
    seed_spells()
