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
SUPERVISOR_SLACK="$JARVIS_DIR/scripts/supervisor_slack.sh"
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

# Spawn Telegram supervisor.
cd "$JARVIS_DIR"
nohup bash "$SUPERVISOR" > logs/supervisor_stdout.log 2>&1 &
disown || true
echo "[$(date -Iseconds)] supervisor (telegram) spawned pid=$!" >> "$HOOK_LOG"

# Spawn Slack supervisor (skip interne s'il n'y a pas de tokens Slack).
if [ -x "$SUPERVISOR_SLACK" ]; then
  if pgrep -f "scripts/supervisor_slack.sh" > /dev/null 2>&1; then
    echo "[$(date -Iseconds)] supervisor_slack already running — skip" >> "$HOOK_LOG"
  else
    nohup bash "$SUPERVISOR_SLACK" > logs/supervisor_slack_stdout.log 2>&1 &
    disown || true
    echo "[$(date -Iseconds)] supervisor_slack spawned pid=$!" >> "$HOOK_LOG"
  fi
fi

exit 0
