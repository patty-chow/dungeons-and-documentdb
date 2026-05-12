"""🍺 The Tavern -- chat with Bram + live memory panel."""
from __future__ import annotations

import streamlit as st

from src.db import get_db
from src.llm import chat
from src.tavern.memory import (
    extract_topics, get_recent_conversations, save_conversation,
)
from src.tavern.npc import BRAM_DEFAULT, build_system_prompt, build_user_prompt
from src.tavern.player import get_or_create_player, learn_quest, record_visit
from webui._shared import get_player_id, jsonable

NPC_ID = "bram_tavern"


def _render_memory_panel(db, player_id: str) -> None:
    """The right-hand 'what Bram remembers' column."""
    st.markdown("### 📜 What Bram remembers")
    player = db.players.find_one({"_id": player_id})
    if not player:
        st.info("New adventurer. Say hello to Bram to begin.")
        return

    st.markdown(f"**Player**: `{player.get('name', 'Adventurer')}`")
    st.markdown(f"**Visits**: {player.get('visit_count', 0)}")
    st.markdown(f"**Reputation**: {player.get('reputation', 'neutral')}")

    quests = player.get("known_quests", [])
    if quests:
        st.markdown("**Known quests**")
        for q in quests:
            st.markdown(f"- `{q}`")
    else:
        st.markdown("**Known quests**: _none yet_")

    st.divider()
    st.markdown("**Recent conversations**")
    convos = list(
        db.conversations
        .find({"player_id": player_id, "npc_id": NPC_ID})
        .sort("timestamp", -1)
        .limit(3)
    )
    if not convos:
        st.markdown("_No memories yet — say something._")
    else:
        for c in convos:
            ts = c["timestamp"].strftime("%H:%M:%S")
            topics = ", ".join(c.get("topics_mentioned", [])) or "—"
            with st.container(border=True):
                st.caption(f"⏱ {ts} · topics: `{topics}`")
                st.markdown(f"**You**: {c['player_message']}")
                snippet = c["npc_response"]
                if len(snippet) > 140:
                    snippet = snippet[:140] + "…"
                st.markdown(f"**Bram**: {snippet}")

        with st.expander("🔍 Peek the raw document"):
            st.json(jsonable(convos[0]))

    st.divider()
    if st.button("🗑 Reset memory", type="secondary", use_container_width=True):
        db.conversations.delete_many({"player_id": player_id})
        db.players.update_one(
            {"_id": player_id},
            {"$set": {
                "visit_count": 0,
                "known_quests": [],
                "reputation": "neutral",
            }},
        )
        st.rerun()


def render_tavern() -> None:
    """Tab 1 entry point."""
    db = get_db()
    player_id = get_player_id()
    npc = db.npcs.find_one({"_id": NPC_ID}) or BRAM_DEFAULT
    get_or_create_player(db, player_id)

    chat_col, panel_col = st.columns([0.58, 0.42], gap="large")

    with chat_col:
        st.markdown(f"### 🍺 {npc.get('location', 'The Rusty Flagon')}")
        st.caption(
            f"You enter the tavern. {npc['name']} looks up from polishing a mug."
        )

        history = get_recent_conversations(db, player_id, NPC_ID, limit=10)
        player = db.players.find_one({"_id": player_id}) or {}
        visits = player.get("visit_count", 0)

        # Opening greeting (rendered as if Bram spoke first).
        if not history:
            greeting = (
                '"Welcome, stranger! First time in these parts?"'
                if visits == 0
                else f'"Ah, back again! That makes {visits} visits now."'
            )
            with st.chat_message("assistant", avatar="🧔"):
                st.markdown(f"**{npc['name']}**: {greeting}")

        for turn in history:
            with st.chat_message("user"):
                st.markdown(turn["player_message"])
            with st.chat_message("assistant", avatar="🧔"):
                st.markdown(f"**{npc['name']}**: {turn['npc_response']}")

    with panel_col:
        _render_memory_panel(db, player_id)

    # Chat input is pinned to the bottom of this tab.
    prompt = st.chat_input("Speak to Bram...", key="tavern_chat_input")
    if not prompt:
        return

    record_visit(db, player_id)
    # Re-fetch player + history AFTER record_visit so the LLM sees the
    # updated visit count and any prior turns from this same session.
    player = db.players.find_one({"_id": player_id}) or {}
    history = get_recent_conversations(db, player_id, NPC_ID, limit=5)

    system = build_system_prompt(npc, player)
    user_msg = build_user_prompt(history, prompt)
    with st.spinner(f"{npc['name']} considers..."):
        reply = chat(system=system, user=user_msg, max_tokens=300).strip()

    topics = extract_topics(prompt + " " + reply)
    save_conversation(
        db,
        player_id=player_id,
        npc_id=NPC_ID,
        npc_name=npc["name"],
        player_message=prompt,
        npc_response=reply,
        topics=topics,
    )
    if any(t in topics for t in ("goblin", "goblins")):
        learn_quest(db, player_id, "goblin_clearing")

    st.rerun()
