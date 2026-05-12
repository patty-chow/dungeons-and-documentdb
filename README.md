# 🐉 Dungeons and DocumentDB

> A PyCon US 2026 demo showing what you can build with **open-source [DocumentDB](https://github.com/documentdb/documentdb)** and a few hundred lines of Python.

Two Dungeons & Dragons themed agents that teach the two patterns Python devs want most: **conversation memory** and **vector search / RAG**.

| Demo | What it does | What you learn |
|------|---------------|----------------|
| 🍺 **The Tavern Keeper** | Chat with Bram, an NPC who remembers you across sessions | Documents, collections, CRUD, schema flexibility |
| 🧙 **The Spell Book** | Ask Elara the Arcane Librarian about D&D spells in plain English | Embeddings, `cosmosSearch` vector indexes, hybrid filters, RAG |

No cloud account. No MongoDB experience required. Runs on a laptop in under five minutes.

---

## 🚀 Run it in GitHub Codespaces (zero local setup)

The fastest way to try the demos. No Docker, no Python, no extensions to install — everything is preconfigured in the devcontainer, including the **DocumentDB for VS Code** extension.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/patty-chow/dungeons-and-documentdb?quickstart=1)

What you get on first launch:

- Python 3.11 workspace container
- DocumentDB running as a sidecar service (reachable at `documentdb:10260`)
- All Python deps installed (`pymongo`, `anthropic`, `openai`, `voyageai`, `streamlit`, `rich`, ...)
- DocumentDB for VS Code extension preinstalled (sidebar → DocumentDB icon)
- Ports `10260` (DB) and `8501` (Streamlit) auto-forwarded
- A `.env` file pre-seeded from `.env.example`

Once the codespace finishes building:

```bash
# 1. Add your LLM key (only needed for the chat demos)
code .env                      # set ANTHROPIC_API_KEY or OPENAI_API_KEY

# 2. Roll for initiative -- data is already loaded
python -m src.tavern.chat      # CLI: tavern keeper
python -m src.spellbook.chat   # CLI: spell book
streamlit run webui/app.py     # Web UI on port 8501
```

To browse the data with the **DocumentDB for VS Code** extension, click the DocumentDB icon in the activity bar and connect with:

```
mongodb://admin:dungeons123!@documentdb:10260/?tls=true&tlsAllowInvalidCertificates=true
```

You should see a `dnd` database with `npcs`, `players`, `conversations`, and `spells` collections preloaded.

> ⚙️ **What if vector search returns nothing?** The shipped pre-embedded data lets the spell book work out-of-the-box. If `data/srd_spells_embedded.json` is missing from your fork, the post-create step loads the raw spell metadata only and the wizard demo's vector search will be disabled until you run `python scripts/seed_all.py` with an LLM key set in `.env`.

---

## ⚡ Quickstart (run locally)

```bash
# 1. Clone
git clone https://github.com/patty-chow/dungeons-and-documentdb.git
cd dungeons-and-documentdb

# 2. Start DocumentDB (Docker)
docker compose up -d

# 3. Install Python deps (Python 3.11+)
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 4. Add your LLM key (only needed for the chat demos)
cp .env.example .env
# Edit .env -- ANTHROPIC_API_KEY=sk-ant-... (or OPENAI_API_KEY=sk-...)

# 5. Load NPCs, the player, and the spell book (uses pre-embedded data,
#    no LLM key required). Vector search works immediately.
python scripts/load_data.py

# 6. Roll for initiative!
python -m src.tavern.chat        # Chat with Bram the tavern keeper
python -m src.spellbook.chat     # Ask Elara about spells
```

> Press `Ctrl+C` or type `/quit` to leave a chat session. Bram remembers across restarts.

> 🔁 **Want to re-embed the spells with your own provider** (e.g. switch from OpenAI to Voyage AI)? Run `python scripts/seed_all.py` instead of `load_data.py` — it regenerates embeddings on the fly using whichever provider is configured in `.env`.

---

## 🎨 Web UI (optional, recommended for live demos)

The CLI demos are the canonical path — they're the smallest amount of code that shows the pattern. But there's also a **Streamlit web UI** that makes the vector retrieval visible in real time, which is much more compelling for a talk.

```bash
streamlit run webui/app.py
```

Opens at [http://localhost:8501](http://localhost:8501) with two views you can switch between via a horizontal scene selector:

- 🍺 **The Tavern** — chat on the left; live memory panel on the right showing visit count, known quests, recent conversation cards, and a "peek the raw document" expander.
- 🧙 **The Athenaeum** — chat on the left; live vector search results on the right, including five spell cards with their cosine similarity scores, filter controls, and a "peek the aggregation pipeline" expander.

Same `src/` code underneath. The UI is purely additive — nothing about the CLI demos changes.

---

## 🎲 Demo 1: The Tavern Keeper

```text
🍺 You enter the Rusty Flagon tavern. Bram looks up from polishing a mug.

Bram: "Welcome, stranger! First time in these parts?"

You: I'm looking for work. Anything dangerous?

Bram: "Dangerous, eh? There's been talk of goblins in the Whisperwood.
The mayor's offering 50 gold to anyone brave enough to clear them out."

You: /quit

# ... later that day ...
$ python -m src.tavern.chat

Bram: "Back already! Did you have a go at those goblins in the
Whisperwood? Last time you seemed keen on the mayor's bounty."
```

Every line of dialogue becomes a document in the `conversations` collection. On startup we fetch the player's recent history and feed it to the LLM as context. **That's it.** That's "agent memory."

---

## 🔮 Demo 2: The Spell Book

```text
🧙 Elara peers over her spectacles.

Elara: "Welcome to the Athenaeum. What arcane knowledge do you seek?"

You: What's a good spell against undead that doesn't need concentration?

Elara: "Three excellent choices from the Athenaeum:

  1. Sacred Flame (cantrip, Evocation) -- radiant damage, no
     concentration, no attack roll required.
  2. Guiding Bolt (1st level, Evocation) -- 4d6 radiant and grants
     advantage on the next attack against the target.
  3. Spirit Guardians (3rd level, Conjuration) -- but this one DOES
     require concentration. Skip it for your needs."
```

Under the hood:

1. Your question is embedded into a vector.
2. DocumentDB's `cosmosSearch` index returns the top-k semantically similar spells.
3. Those spell documents (plus your question) are passed to the LLM.
4. Elara answers using only what was retrieved -- classic RAG.

---

## 🏗️ Project Layout

```
dungeons-and-documentdb/
├── docker-compose.yml          # DocumentDB local
├── requirements.txt
├── .env.example
├── data/
│   └── srd_spells.json         # 50 5e SRD spells (CC-BY-4.0)
├── src/
│   ├── db.py                   # DocumentDB connection helpers
│   ├── embeddings.py           # Voyage / OpenAI embedding client
│   ├── llm.py                  # Claude / OpenAI chat client
│   ├── tavern/                 # Demo 1: NPC memory agent
│   │   ├── npc.py
│   │   ├── memory.py
│   │   ├── player.py
│   │   └── chat.py
│   └── spellbook/              # Demo 2: Vector search RAG agent
│       ├── search.py
│       ├── wizard.py
│       ├── seed.py
│       └── chat.py
├── scripts/
│   ├── setup_db.py             # Create collections + indexes
│   └── seed_all.py             # Populate NPCs, player, spells
├── webui/                      # Optional Streamlit UI
│   ├── app.py
│   ├── tavern_view.py
│   └── spellbook_view.py
└── tests/
```

---

## 🧰 Tech Stack

| Component | Choice |
|-----------|--------|
| Database  | [OSS DocumentDB](https://github.com/documentdb/documentdb) (Docker, port `10260`) |
| Driver    | `pymongo` (DocumentDB speaks the MongoDB wire protocol) |
| LLM       | Anthropic Claude (preferred), OpenAI (fallback) |
| Embeddings| Voyage AI via Anthropic, OR OpenAI `text-embedding-3-small` |
| CLI       | `rich` |

---

## 🧪 Inspecting the Data

Use [`mongosh`](https://www.mongodb.com/docs/mongodb-shell/) or any MongoDB client:

```bash
mongosh "mongodb://admin:dungeons123!@localhost:10260/?tls=true&tlsAllowInvalidCertificates=true"

> use dnd
> db.conversations.find().sort({timestamp:-1}).limit(3).pretty()
> db.spells.findOne({name:"Fireball"})
```

---

## 🛠️ Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ServerSelectionTimeoutError` | `docker compose ps` -- container takes ~10s on first boot. |
| `Authentication failed` | The `.env` `DOCUMENTDB_PASSWORD` must match `docker-compose.yml`. |
| `OperationFailure: command createIndexes ... vector` | You're on an older DocumentDB image. `docker compose pull && docker compose up -d`. |
| Spells return weird results | Re-run `python scripts/seed_all.py` -- embeddings may have failed mid-seed. |
| Windows + `source .venv/...` | Use `.venv\Scripts\activate` instead. |
| `No LLM provider configured` | Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in `.env`. |

---

## 🐲 Make It Yours

Fork it. Then:

- **Add NPCs.** Drop a new doc into the `npcs` collection. Point `tavern/chat.py` at the new `npc_id`.
- **Add spells.** Append to `data/srd_spells.json` (SRD content only, please) and re-run `seed_all.py`.
- **Wire in tools.** Give Bram a tool to actually post quests to a `quests` collection.
- **Hot-swap LLMs.** The same code runs on Claude or OpenAI -- just change which key is set.

---

## 🛠️ For Maintainers: Regenerating the Pre-Embedded Spell Data

`scripts/load_data.py` (run automatically in Codespaces and as step 5 of the local quickstart) prefers `data/srd_spells_embedded.json` because it lets new users get a working vector-search demo with **no embedding API key**. If you change `data/srd_spells.json` (add/edit spells, change `_embedding_input` shape), regenerate the embedded copy and commit it:

```bash
# Use OpenAI for the shipped data (1536 dims, widely supported)
OPENAI_API_KEY=sk-... python scripts/generate_embeddings.py
git add data/srd_spells_embedded.json
git commit -m "Regenerate spell embeddings"
```

This file is intentionally NOT in `.gitignore` -- it's a deliberate artifact shipped with the repo so the demo works on first boot.

---

## 📜 Credits & License

- Demo code: **MIT** -- see [LICENSE](./LICENSE).
- Spell data in `data/srd_spells.json`: **CC-BY-4.0**, derived from the [Systems Reference Document 5.1](https://dnd.wizards.com/resources/systems-reference-document) by Wizards of the Coast LLC.
- DocumentDB is MIT-licensed by the DocumentDB project contributors.

Built for [PyCon US 2026](https://us.pycon.org/2026/) by [@patty-chow](https://github.com/patty-chow). 🐍
