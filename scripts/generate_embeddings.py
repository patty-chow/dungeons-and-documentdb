"""One-time embedding generation for the shipped spell data.

Run this ONCE (locally, with an embedding API key) to produce
`data/srd_spells_embedded.json`. That file is then committed and used by
`scripts/load_data.py` so codespace users (and anyone else) can populate
the database with working vector search WITHOUT needing their own
embedding API key first.

Usage:
    # With OpenAI (recommended for shipped data -- 1536 dims, widely supported)
    OPENAI_API_KEY=sk-... python scripts/generate_embeddings.py

    # Or with Voyage AI
    VOYAGE_API_KEY=pa-... python scripts/generate_embeddings.py

The user's later `seed_all.py` runs still re-embed with their own provider
of choice, so there's no lock-in -- this is just to bootstrap the demo.
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
from rich.progress import Progress  # noqa: E402

from src.embeddings import embed_batch, provider_name  # noqa: E402
from src.spellbook.seed import _embedding_input  # noqa: E402

console = Console()

SOURCE = _PROJECT_ROOT / "data" / "srd_spells.json"
OUTPUT = _PROJECT_ROOT / "data" / "srd_spells_embedded.json"


def main(batch_size: int = 16) -> None:
    if not SOURCE.exists():
        console.print(f"[red]Source not found: {SOURCE}[/red]")
        sys.exit(1)

    spells: list[dict] = json.loads(SOURCE.read_text(encoding="utf-8"))
    console.rule(f"[bold]Embedding {len(spells)} spells[/bold]")
    console.print(f"Provider: [bold]{provider_name()}[/bold]")
    console.print(f"Output:   {OUTPUT}")

    with Progress() as bar:
        task = bar.add_task("Embedding...", total=len(spells))
        for i in range(0, len(spells), batch_size):
            chunk = spells[i:i + batch_size]
            vectors = embed_batch([_embedding_input(s) for s in chunk])
            for s, v in zip(chunk, vectors):
                s["embedding"] = v
            bar.advance(task, advance=len(chunk))

    dims = len(spells[0]["embedding"])
    payload = {
        "_metadata": {
            "embedding_provider": provider_name(),
            "dimensions": dims,
            "spell_count": len(spells),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": SOURCE.name,
        },
        "spells": spells,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    console.rule("[bold green]Done[/bold green]")
    console.print(
        f"Wrote {OUTPUT.name} ({len(spells)} spells, {dims}-dim vectors). "
        "Commit it so codespace users get a working DB on first boot."
    )


if __name__ == "__main__":
    main()
