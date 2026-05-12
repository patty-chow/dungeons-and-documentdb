"""Elara the Arcane Librarian -- CLI chat loop.

Run from the project root:
    python -m src.spellbook.chat
"""
from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from src.db import get_db, ping
from src.llm import provider_name
from src.spellbook.wizard import answer

console = Console()


def _banner() -> None:
    console.print(Panel.fit(
        "[bold magenta]🧙 Elara the Arcane Librarian peers over her "
        "spectacles.[/bold magenta]\n"
        '[dim]"Welcome to the Athenaeum. What arcane knowledge do you '
        'seek?"[/dim]\n\n'
        "[dim]Type a question. /quit to leave. "
        "/show to see the spells she just consulted.[/dim]",
        border_style="magenta", title="The Athenaeum",
    ))


def _show_spells(spells: list[dict]) -> None:
    if not spells:
        console.print("[dim]No spells were retrieved.[/dim]")
        return
    table = Table(title="📚 Spells consulted (vector search results)")
    table.add_column("Score", justify="right", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("Lvl", justify="right")
    table.add_column("School")
    table.add_column("Conc?")
    for s in spells:
        score = f"{s.get('score', 0):.3f}"
        lvl = "0" if s["level"] == 0 else str(s["level"])
        conc = "✓" if s.get("concentration") else ""
        table.add_row(score, s["name"], lvl, s["school"], conc)
    console.print(table)


def run() -> None:
    if not ping():
        console.print(
            "[red]❌ Could not reach DocumentDB. "
            "Is `docker compose up -d` running?[/red]"
        )
        sys.exit(1)

    db = get_db()
    if db.spells.count_documents({}) == 0:
        console.print(
            "[red]❌ The spells collection is empty.[/red]\n"
            "[dim]Run: python scripts/seed_all.py[/dim]"
        )
        sys.exit(1)

    _banner()
    console.print(f"[dim](chatting via {provider_name()})[/dim]\n")

    last_spells: list[dict] = []
    while True:
        try:
            q = Prompt.ask("[bold cyan]You[/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Elara nods and returns to her tome.[/dim]")
            return

        cmd = q.strip().lower()
        if cmd in {"/quit", "/exit", "/bye"}:
            console.print("[dim]Elara nods and returns to her tome.[/dim]")
            return
        if cmd == "/show":
            _show_spells(last_spells)
            continue
        if not q.strip():
            continue

        reply, last_spells = answer(db, q)
        console.print(f"\n[bold magenta]Elara:[/bold magenta] {reply}\n")


if __name__ == "__main__":
    run()
