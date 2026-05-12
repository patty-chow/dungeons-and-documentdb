#!/usr/bin/env bash
# Runs once after the devcontainer is built. Installs Python dependencies,
# bootstraps the .env file, and waits for DocumentDB to come up.
set -euo pipefail

echo "==> Installing Python dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e ".[dev]"

echo "==> Bootstrapping .env..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "    .env created from template."
  echo "    Add ANTHROPIC_API_KEY or OPENAI_API_KEY before running the demos."
else
  echo "    .env already exists, leaving it untouched."
fi

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

  The database is preloaded with NPCs, the demo player, and the
  spell book. Browse it with the DocumentDB extension in the
  sidebar -- click the DocumentDB icon and add this connection:

    mongodb://admin:dungeons123!@documentdb:10260/?tls=true&tlsAllowInvalidCertificates=true

  To chat with the NPCs you need an LLM key:
    1. Edit .env and set ANTHROPIC_API_KEY or OPENAI_API_KEY.
    2. Run a demo:
         python -m src.tavern.chat        # CLI: tavern keeper
         python -m src.spellbook.chat     # CLI: spell book
         streamlit run webui/app.py       # Web UI (port 8501)

  If the spells loaded without embeddings (no srd_spells_embedded.json
  shipped), regenerate them with your own key:
         python scripts/seed_all.py
================================================================
EOF
