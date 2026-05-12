"""Shared utilities for the Streamlit UI.

Bootstraps sys.path, provides status pills, sidebar, and a few helpers used
by both tabs.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `from src...` work whether streamlit is launched from the project
# root or from inside webui/.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from src.db import ping  # noqa: E402

DEFAULT_PLAYER_ID = "adventurer_001"


def _pill(label: str, ok: bool, detail: str) -> str:
    icon = "🟢" if ok else "🔴"
    return f"{icon} **{label}** · {detail}"


def render_status_bar() -> bool:
    """Render the DocumentDB / LLM / Embeddings status row.

    Returns True if all three are reachable / configured.
    """
    db_ok = ping()
    db_detail = "reachable" if db_ok else "run `docker compose up -d`"

    llm_ok, llm_detail = False, "not configured"
    try:
        from src.llm import provider_name as llm_provider
        llm_detail = llm_provider()
        llm_ok = True
    except Exception as e:
        llm_detail = str(e).split("\n", 1)[0]

    emb_ok, emb_detail = False, "not configured"
    try:
        from src.embeddings import provider_name as emb_provider
        emb_detail = emb_provider()
        emb_ok = True
    except Exception as e:
        emb_detail = str(e).split("\n", 1)[0]

    cols = st.columns(3)
    cols[0].markdown(_pill("DocumentDB", db_ok, db_detail))
    cols[1].markdown(_pill("LLM", llm_ok, llm_detail))
    cols[2].markdown(_pill("Embeddings", emb_ok, emb_detail))

    return db_ok and llm_ok and emb_ok


def render_sidebar() -> None:
    """Render the global sidebar with persona switcher and links."""
    with st.sidebar:
        st.markdown("## 🐉 Settings")
        st.text_input(
            "Player ID",
            value=DEFAULT_PLAYER_ID,
            key="player_id_input",
            help=(
                "Switch personas. Each ID gets its own memory in the "
                "`players` and `conversations` collections."
            ),
        )

        st.divider()
        st.markdown("### About")
        st.markdown(
            "A PyCon US 2026 demo built on open-source "
            "[DocumentDB](https://github.com/documentdb/documentdb).\n\n"
            "Two patterns, ~600 lines of Python:\n"
            "- 🍺 **Tavern** — conversation memory\n"
            "- 🧙 **Athenaeum** — vector search RAG\n\n"
            "[View source on GitHub]"
            "(https://github.com/patty-chow/dungeons-and-documentdb)"
        )


def get_player_id() -> str:
    """Return the player ID currently selected in the sidebar."""
    return st.session_state.get("player_id_input", DEFAULT_PLAYER_ID)


def jsonable(doc: dict) -> dict:
    """Convert pymongo result types (ObjectId, datetime) to JSON-friendly."""
    from datetime import datetime
    out: dict = {}
    for k, v in doc.items():
        if isinstance(v, datetime):
            out[k] = v.isoformat()
        elif hasattr(v, "binary"):  # ObjectId
            out[k] = str(v)
        elif isinstance(v, list):
            out[k] = [jsonable(x) if isinstance(x, dict) else x for x in v]
        elif isinstance(v, dict):
            out[k] = jsonable(v)
        else:
            out[k] = v
    return out
