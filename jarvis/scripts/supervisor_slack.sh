#!/usr/bin/env bash
# Supervise le bot Slack — redémarre auto s'il meurt.
# Log logs/slack.log (bot) + logs/supervisor_slack.log (watchdog).
# Skip immédiat si SLACK_BOT_TOKEN ou SLACK_APP_TOKEN manquants.
set -e
cd "$(dirname "$0")/.."

LOG=logs/supervisor_slack.log
BOT_LOG=logs/slack.log
mkdir -p logs

set -a
. ./.env 2>/dev/null || true
set +a

export PYTHONPATH=.

if [ -z "${SLACK_BOT_TOKEN:-}" ] || [ -z "${SLACK_APP_TOKEN:-}" ]; then
  echo "[$(date -Iseconds)] SLACK_BOT_TOKEN ou SLACK_APP_TOKEN absent — skip supervisor_slack" >> "$LOG"
  exit 0
fi

echo "[$(date -Iseconds)] supervisor_slack start" >> "$LOG"
while true; do
  echo "[$(date -Iseconds)] spawning slack bot" >> "$LOG"
  python3 -m jarvis.slack_bot.bot >> "$BOT_LOG" 2>&1
  code=$?
  echo "[$(date -Iseconds)] slack bot exited code=$code — restart in 3s" >> "$LOG"
  sleep 3
done
