"""The Tavern Keeper -- CLI chat loop for Bram the NPC.

Run from the project root:
    python -m src.tavern.chat
"""
from __future__ import annotations

import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from src.db import get_db, ping
from src.llm import chat, provider_name
from src.tavern.memory import (
    extract_topics, get_recent_conversations, save_conversation,
)
from src.tavern.npc import BRAM_DEFAULT, build_system_prompt, build_user_prompt
from src.tavern.player import get_or_create_player, learn_quest, record_visit

console = Console()

NPC_ID = "bram_tavern"
PLAYER_ID = os.getenv("PLAYER_ID", "adventurer_001")


def _banner(npc_name: str) -> None:
    console.print(Panel.fit(
        f"[bold yellow]🍺 You enter the Rusty Flagon tavern.[/bold yellow]\n"
        f"[dim]{npc_name} the tavern keeper looks up from polishing a mug.[/dim]\n\n"
        "[dim]Type your message and press Enter. "
        "Type [bold]/quit[/bold] to leave.[/dim]",
        border_style="yellow", title="The Rusty Flagon",
    ))


def run() -> None:
    if not ping():
        console.print(
            "[red]❌ Could not reach DocumentDB. "
            "Is `docker compose up -d` running?[/red]"
        )
        sys.exit(1)

    db = get_db()
    npc = db.npcs.find_one({"_id": NPC_ID}) or BRAM_DEFAULT
    player = get_or_create_player(db, PLAYER_ID)
    history = get_recent_conversations(db, PLAYER_ID, NPC_ID, limit=5)

    _banner(npc["name"])
    record_visit(db, PLAYER_ID)
    player = db.players.find_one({"_id": PLAYER_ID}) or player

    console.print(f"[dim](chatting via {provider_name()})[/dim]\n")

    # Greeting: returning visitor vs first-timer.
    if history:
        console.print(
            f'[bold yellow]{npc["name"]}:[/bold yellow] '
            '"Ah, back again! What can I get you?"'
        )
    else:
        console.print(
            f'[bold yellow]{npc["name"]}:[/bold yellow] '
            '"Welcome, stranger! First time in these parts?"'
        )

    while True:
        try:
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]The door swings shut behind you.[/dim]")
            return

        if user_input.strip().lower() in {"/quit", "/exit", "/bye"}:
            console.print("[dim]The door swings shut behind you.[/dim]")
            return
        if not user_input.strip():
            continue

        system = build_system_prompt(npc, player)
        user = build_user_prompt(history, user_input)
        reply = chat(system=system, user=user, max_tokens=300).strip()

        console.print(f"\n[bold yellow]{npc['name']}:[/bold yellow] {reply}")

        topics = extract_topics(user_input + " " + reply)
        save_conversation(
            db,
            player_id=PLAYER_ID,
            npc_id=NPC_ID,
            npc_name=npc["name"],
            player_message=user_input,
            npc_response=reply,
            topics=topics,
        )

        # Toy quest extraction: if goblins came up, mark the quest known.
        if any(t in topics for t in ("goblin", "goblins")):
            learn_quest(db, PLAYER_ID, "goblin_clearing")

        # Keep an in-memory rolling window of the last 5 turns.
        history.append({
            "player_message": user_input,
            "npc_response": reply,
            "npc_name": npc["name"],
        })
        history[:] = history[-5:]


if __name__ == "__main__":
    run()
