#!/usr/bin/env bash
# autodeploy.sh — déploiement autonome sur le VPS.
# À lancer périodiquement (cron). Si la branche distante a avancé, il met à
# jour le code et reconstruit le conteneur. Sinon il ne fait rien.
#
# Active-le une fois (cron toutes les 5 min) :
#   ( crontab -l 2>/dev/null; \
#     echo "*/5 * * * * bash /opt/deco/company/deploy/autodeploy.sh >> /opt/deco/company/state/autodeploy.log 2>&1" \
#   ) | crontab -
#
# .env et state/ sont gitignorés → préservés par le reset (untracked).
set -uo pipefail

COMPANY_DIR="$(cd "$(dirname "$0")/.." && pwd)"        # .../company
REPO_DIR="$(git -C "$COMPANY_DIR" rev-parse --show-toplevel)"
BRANCH="$(git -C "$REPO_DIR" rev-parse --abbrev-ref HEAD)"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

git -C "$REPO_DIR" fetch origin "$BRANCH" -q || { echo "$TS fetch KO"; exit 0; }
LOCAL="$(git -C "$REPO_DIR" rev-parse HEAD)"
REMOTE="$(git -C "$REPO_DIR" rev-parse "origin/$BRANCH")"

if [ "$LOCAL" = "$REMOTE" ]; then
  exit 0   # déjà à jour, rien à faire
fi

echo "$TS nouvelle version détectée ($LOCAL -> $REMOTE), déploiement…"
git -C "$REPO_DIR" reset --hard "origin/$BRANCH"      # untracked (.env, state/) préservés
cd "$COMPANY_DIR"
docker compose up -d --build
echo "$TS déploiement terminé."
