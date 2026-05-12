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
for i in $(seq 1 $ATTEMPTS); do
  if python -c "from src.db import ping; import sys; sys.exit(0 if ping() else 1)" 2>/dev/null; then
    echo "    DocumentDB is ready."
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

cat <<'EOF'

================================================================
  Codespace ready.

  Next steps:
    1. Add an LLM API key to .env (ANTHROPIC_API_KEY or OPENAI_API_KEY).
    2. Seed the realm:
         python scripts/seed_all.py
    3. Run a demo:
         python -m src.tavern.chat        # CLI: tavern keeper
         python -m src.spellbook.chat     # CLI: spell book
         streamlit run webui/app.py       # Web UI (port 8501)

  Use the DocumentDB for VS Code extension (sidebar) to browse data:
    Connection string:
      mongodb://admin:dungeons123!@documentdb:10260/?tls=true&tlsAllowInvalidCertificates=true
================================================================
EOF
