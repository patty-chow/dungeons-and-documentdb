"""🐉 Dungeons and DocumentDB -- Streamlit web UI entry point.

Launch from the project root:
    streamlit run webui/app.py
"""
from __future__ import annotations

# Make `from src...` work BEFORE we import the inner modules.
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st  # noqa: E402

from webui._shared import render_sidebar, render_status_bar  # noqa: E402
from webui.spellbook_view import render_spellbook  # noqa: E402
from webui.tavern_view import render_tavern  # noqa: E402

st.set_page_config(
    page_title="Dungeons and DocumentDB",
    page_icon="🐉",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    "# 🐉 Dungeons and DocumentDB",
    help="A PyCon US 2026 demo built on open-source DocumentDB.",
)
st.caption(
    "Two D&D-themed agents that show what a few hundred lines of Python "
    "and `cosmosSearch` can do."
)

render_sidebar()
all_ok = render_status_bar()

if not all_ok:
    st.warning(
        "Some prerequisites are missing. Check the status pills above — "
        "either `docker compose up -d` is not running, or your `.env` is "
        "missing an LLM / embedding API key."
    )

tab_tavern, tab_spell = st.tabs(["🍺 The Tavern", "🧙 The Athenaeum"])

with tab_tavern:
    render_tavern()

with tab_spell:
    render_spellbook()
