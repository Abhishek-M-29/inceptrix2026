#!/bin/bash
set -e

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

if [ -z "$REPO_URL" ]; then
  log "ERROR: REPO_URL environment variable is not set."
  exit 1
fi

log "Cloning $REPO_URL..."
git clone "$REPO_URL" /app
log "Clone complete."

cd /app

log "Installing npm dependencies..."
npm install
log "Dependencies installed."

log "Starting Vite dev server on 0.0.0.0:5173..."
exec npm run dev -- --host
