#!/usr/bin/env bash
set -e

# Audio Durations — production start script for Oracle Cloud Free Tier
#
# Usage:
#   chmod +x start.sh
#   ./start.sh
#
# Environment variables:
#   PORT          — server port (default: 5000)
#   WORKERS       — gunicorn worker count (default: 2)

PORT="${PORT:-5000}"
WORKERS="${WORKERS:-2}"

echo "==> Installing dependencies..."
pip install -q -r requirements.txt

echo "==> Starting server on 0.0.0.0:${PORT} with ${WORKERS} worker(s)..."
exec gunicorn \
  --workers "$WORKERS" \
  --bind "0.0.0.0:${PORT}" \
  --timeout 300 \
  --keep-alive 5 \
  --log-level info \
  app:app
