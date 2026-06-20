#!/usr/bin/env bash
# audit_hook.sh — hook de logging léger (garde-fou transverse).
# À brancher dans .claude/settings.json (PostToolUse) si souhaité.
# Journalise un horodatage + l'événement reçu dans state/hook_audit.log.
# Le journal d'audit faisant autorité reste audit_log (company.db) ; ce hook
# est une trace de surface, complémentaire.

set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG="$DIR/state/hook_audit.log"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
INPUT="$(cat || true)"
printf '%s %s\n' "$TS" "${INPUT:-<no-input>}" >> "$LOG"
