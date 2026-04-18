#!/bin/bash
# SessionStart hook : relance le supervisor bot Telegram Jarvis s'il est mort.
#
# Idempotent : si le supervisor tourne déjà, on ne fait rien.
# Non-bloquant : supervisor lancé en background, hook retourne <1s.
# Logs : jarvis/logs/hook.log
set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-/home/user/test}"
JARVIS_DIR="$PROJECT_DIR/jarvis"
SUPERVISOR="$JARVIS_DIR/scripts/supervisor.sh"
HOOK_LOG="$JARVIS_DIR/logs/hook.log"

mkdir -p "$JARVIS_DIR/logs"
echo "[$(date -Iseconds)] session-start hook triggered (source=${1:-?})" >> "$HOOK_LOG"

# Déjà vivant ?
if pgrep -f "scripts/supervisor.sh" > /dev/null 2>&1; then
  echo "[$(date -Iseconds)] supervisor already running — skip" >> "$HOOK_LOG"
  exit 0
fi

# Pas de supervisor sur disque ? Rien à faire.
if [ ! -x "$SUPERVISOR" ]; then
  echo "[$(date -Iseconds)] supervisor.sh absent ou non exécutable — skip" >> "$HOOK_LOG"
  exit 0
fi

# Pas de .env ? Rien à faire (mode dev sans token).
if [ ! -f "$JARVIS_DIR/.env" ]; then
  echo "[$(date -Iseconds)] .env absent — bot non démarré" >> "$HOOK_LOG"
  exit 0
fi

# Spawn en background, detached, stdout/stderr redirigés.
cd "$JARVIS_DIR"
nohup bash "$SUPERVISOR" > logs/supervisor_stdout.log 2>&1 &
disown || true

echo "[$(date -Iseconds)] supervisor spawned pid=$!" >> "$HOOK_LOG"
exit 0
