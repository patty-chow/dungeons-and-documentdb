#!/usr/bin/env bash
# Runs once after the devcontainer is built. Installs Python dependencies,
# bootstraps the .env file, starts DocumentDB via docker compose, waits for
# it to come up, then loads sample data.
set -euo pipefail

echo "==> Installing Python dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e ".[dev]"

echo "==> Bootstrapping .env..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "    .env created from template."
  echo "    Add OPENAI_API_KEY before running the chat demos."
else
  echo "    .env already exists, leaving it untouched."
fi

echo "==> Starting DocumentDB container..."
# Uses the project's root docker-compose.yml. Same command a local user runs.
docker compose up -d documentdb

echo "==> Waiting for DocumentDB to accept connections..."
ATTEMPTS=30
DB_READY=0
for i in $(seq 1 $ATTEMPTS); do
  if python -c "from src.db import ping; import sys; sys.exit(0 if ping() else 1)" 2>/dev/null; then
    echo "    DocumentDB is ready."
    DB_READY=1
    break
  fi
  if [ "$i" -eq "$ATTEMPTS" ]; then
    echo "    DocumentDB did not respond after $ATTEMPTS attempts."
    echo "    Check 'docker compose logs documentdb' or rebuild the container."
  else
    echo "    ...not ready yet (attempt $i/$ATTEMPTS), retrying in 2s"
    sleep 2
  fi
done

if [ "$DB_READY" -eq 1 ]; then
  echo "==> Loading sample data..."
  # load_data.py uses pre-embedded spells if data/srd_spells_embedded.json
  # exists (no LLM key needed). Falls back to raw spells otherwise.
  python scripts/load_data.py || echo "    (data load reported errors -- see output above)"
fi

cat <<'EOF'

================================================================
  Codespace ready.

  DocumentDB is running as a Docker container managed by the
  project's docker-compose.yml. Inspect it any time:

    docker compose ps
    docker compose logs documentdb
    docker compose restart documentdb

  Browse the data with the DocumentDB extension in the sidebar.
  Click the DocumentDB icon and add this connection:

    mongodb://admin:dungeons123!@localhost:10260/?tls=true&tlsAllowInvalidCertificates=true

  To chat with the NPCs you need an LLM key:
    1. Edit .env and set OPENAI_API_KEY (recommended -- one key powers
       both chat and the spell book's vector search). ANTHROPIC_API_KEY
       also works for chat, but you still need OPENAI_API_KEY for the
       spell book to match the shipped pre-embedded data.
    2. Run a demo:
         python -m src.tavern.chat        # CLI: tavern keeper
         python -m src.spellbook.chat     # CLI: spell book
         streamlit run webui/app.py       # Web UI (port 8501)

  If the spells loaded without embeddings, regenerate them with
  your own key:
         python scripts/seed_all.py
================================================================
EOF
