#!/usr/bin/env bash
# agent_loop.sh — boucle 24/7 de l'agent CEO pour un VPS.
#
# Fait deux choses en continu :
#   - DIALOGUE : lit Slack et répond (--listen) toutes les LISTEN_INTERVAL s.
#   - GESTION  : exécute un cycle de management toutes les CYCLE_EVERY s.
#
# Sûr par défaut : les cycles tournent en --dry-run. Passe en réel en mettant
# COMPANY_ALLOW_LIVE=1 dans company/.env (les actions ROUGE restent toujours
# en file d'approbation, jamais exécutées sans toi).
#
# Réglages (via env ou company/.env) :
#   LISTEN_INTERVAL  (défaut 30)    secondes entre deux lectures Slack
#   CYCLE_EVERY      (défaut 3600)  secondes entre deux cycles (1h)
set -uo pipefail
cd "$(dirname "$0")/.."        # -> dossier company/

LISTEN_INTERVAL="${LISTEN_INTERVAL:-30}"
CYCLE_EVERY="${CYCLE_EVERY:-3600}"
PY="${PYTHON:-python3}"

# Mode de cycle : dry-run par défaut, live si explicitement autorisé.
CYCLE_FLAGS="--cycle --dry-run"
if grep -qE '^COMPANY_ALLOW_LIVE=1' .env 2>/dev/null || [ "${COMPANY_ALLOW_LIVE:-}" = "1" ]; then
  CYCLE_FLAGS="--cycle --live"
fi

# Bootstrap idempotent (crée la DB si absente, synchronise les agents).
"$PY" orchestrator/orchestrator.py --bootstrap || true

echo "[agent_loop] démarré : listen=${LISTEN_INTERVAL}s, cycle=${CYCLE_EVERY}s, mode='${CYCLE_FLAGS}'"
last_cycle=0
while true; do
  # 1) Dialogue Slack (lit les nouveaux messages et répond)
  "$PY" orchestrator/orchestrator.py --listen || echo "[agent_loop] listen a échoué (on continue)"

  # 2) Cycle de gestion périodique
  now=$(date +%s)
  if [ $(( now - last_cycle )) -ge "$CYCLE_EVERY" ]; then
    "$PY" orchestrator/orchestrator.py $CYCLE_FLAGS || echo "[agent_loop] cycle a échoué (on continue)"
    last_cycle=$now
  fi

  sleep "$LISTEN_INTERVAL"
done
