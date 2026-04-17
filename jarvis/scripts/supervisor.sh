#!/usr/bin/env bash
# Supervise le bot Telegram — redémarre automatiquement s'il meurt.
# Log jarvis/logs/telegram.log (bot) + jarvis/logs/supervisor.log (watchdog).
set -e
cd "$(dirname "$0")/.."

LOG=logs/supervisor.log
BOT_LOG=logs/telegram.log
mkdir -p logs

# Charge .env
set -a
. ./.env 2>/dev/null || true
set +a

export PYTHONPATH=.

echo "[$(date -Iseconds)] supervisor start" >> "$LOG"
while true; do
  echo "[$(date -Iseconds)] spawning bot" >> "$LOG"
  python3 -m jarvis.telegram_bot.bot >> "$BOT_LOG" 2>&1
  code=$?
  echo "[$(date -Iseconds)] bot exited code=$code — restart in 3s" >> "$LOG"
  sleep 3
done
