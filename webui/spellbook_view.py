"""🧙 The Athenaeum -- chat with Elara + live vector search panel."""
from __future__ import annotations

import streamlit as st

from src.db import get_db
from src.spellbook.wizard import answer


def _build_display_pipeline(filters: dict | None, k: int) -> list[dict]:
    """Mirror of the pipeline used internally, with the vector elided.

    We build a separate copy for display so the actual query (with its
    embedded vector) stays tidy, and the audience sees the SHAPE.
    """
    pipeline: list[dict] = [
        {
            "$search": {
                "cosmosSearch": {
                    "vector": "<embedding of your question, e.g. 1024 floats>",
                    "path": "embedding",
                    "k": k,
                }
            }
        },
        {
            "$project": {
                "name": 1, "level": 1, "school": 1, "casting_time": 1,
                "range": 1, "components": 1, "duration": 1,
                "concentration": 1, "description": 1, "damage_type": 1,
                "classes": 1, "tags": 1,
                "score": {"$meta": "searchScore"},
            }
        },
    ]
    if filters:
        pipeline.append({"$match": filters})
    return pipeline


def _render_spell_card(spell: dict) -> None:
    """One row in the 'spells consulted' panel."""
    score = spell.get("score", 0.0)
    lvl = "Cantrip" if spell.get("level") == 0 else f"Level {spell.get('level')}"
    school = spell.get("school", "—")
    conc = "✦ concentration" if spell.get("concentration") else "✓ no concentration"
    dmg = spell.get("damage_type")

    with st.container(border=True):
        c1, c2 = st.columns([1, 4])
        with c1:
            st.markdown(f"<h2 style='margin:0;font-family:monospace;'>"
                        f"{score:.2f}</h2>", unsafe_allow_html=True)
            st.caption("score")
        with c2:
            st.markdown(f"**{spell.get('name', '?')}**")
            tag_line = f"{lvl} · {school} · {conc}"
            if dmg:
                tag_line += f" · {dmg}"
            st.caption(tag_line)
            desc = spell.get("description", "") or ""
            snippet = desc[:200] + ("…" if len(desc) > 200 else "")
            st.markdown(f"_{snippet}_")


def _render_spell_panel(spells: list[dict], pipeline: list[dict] | None) -> None:
    """The right-hand 'spells consulted' column."""
    st.markdown("### 📚 Spells Elara consulted")
    st.caption("Vector search · `cosmosSearch` · top-k from the spell archive")

    if not spells:
        st.info(
            "Ask a question — Elara will search the archive and "
            "show her sources here."
        )
        return

    for s in spells:
        _render_spell_card(s)

    if pipeline:
        with st.expander("🔍 Peek the aggregation pipeline"):
            st.json(pipeline)


def render_spellbook() -> None:
    """Tab 2 entry point."""
    db = get_db()

    if db.spells.count_documents({}) == 0:
        st.warning(
            "📚 **The spell archive is empty.** Run "
            "`python scripts/seed_all.py` to populate it (this loads 50 "
            "SRD spells, generates embeddings, and builds the vector index)."
        )
        return

    # Session-state defaults.
    st.session_state.setdefault("sb_history", [])
    st.session_state.setdefault("sb_last_spells", [])
    st.session_state.setdefault("sb_last_pipeline", None)

    chat_col, panel_col = st.columns([0.55, 0.45], gap="large")

    with chat_col:
        st.markdown("### 🧙 The Athenaeum")
        st.caption("Elara, the Arcane Librarian, peers over her spectacles.")

        if not st.session_state.sb_history:
            with st.chat_message("assistant", avatar="🧙"):
                st.markdown(
                    "**Elara**: \"Welcome to the Athenaeum. What arcane "
                    "knowledge do you seek?\""
                )

        for msg in st.session_state.sb_history:
            with st.chat_message(msg["role"], avatar=msg.get("avatar")):
                st.markdown(msg["content"])

        st.divider()
        with st.expander("🎛 Filters (applied to your next question)"):
            fcol1, fcol2 = st.columns(2)
            with fcol1:
                st.checkbox(
                    "Exclude concentration spells",
                    key="filter_no_conc",
                    help=(
                        "Adds `{'concentration': false}` to the $match stage."
                    ),
                )
            with fcol2:
                st.slider(
                    "Max spell level",
                    min_value=0, max_value=9, value=9,
                    key="filter_max_level",
                    help="0 = cantrips only. 9 = no upper bound.",
                )

    with panel_col:
        _render_spell_panel(
            st.session_state.sb_last_spells,
            st.session_state.sb_last_pipeline,
        )

    prompt = st.chat_input(
        "Ask Elara a question...", key="spellbook_chat_input"
    )
    if not prompt:
        return

    filters: dict = {}
    if st.session_state.get("filter_no_conc"):
        filters["concentration"] = False
    max_lvl = st.session_state.get("filter_max_level", 9)
    if max_lvl < 9:
        filters["level"] = {"$lte": max_lvl}

    st.session_state.sb_history.append({"role": "user", "content": prompt})

    with st.spinner("Elara consults the Athenaeum..."):
        reply, spells = answer(db, prompt, k=5, filters=filters or None)

    st.session_state.sb_history.append({
        "role": "assistant",
        "avatar": "🧙",
        "content": f"**Elara**: {reply}",
    })
    st.session_state.sb_last_spells = spells
    st.session_state.sb_last_pipeline = _build_display_pipeline(
        filters or None, k=5
    )

    st.rerun()
