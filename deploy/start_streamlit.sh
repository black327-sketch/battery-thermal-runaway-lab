#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/digital-lab}"
VENV_DIR="${VENV_DIR:-$APP_DIR/.venv}"
HOST="${STREAMLIT_HOST:-127.0.0.1}"
PORT="${STREAMLIT_PORT:-8501}"

cd "$APP_DIR"
exec "$VENV_DIR/bin/streamlit" run app/main.py \
  --server.address "$HOST" \
  --server.port "$PORT" \
  --server.headless true \
  --browser.gatherUsageStats false
