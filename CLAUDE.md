# CLAUDE.md — Jarvis v6

## Contexte

Écosystème Jarvis v6 dans `jarvis/`. Spec complète dans `jarvis/README.md` et `jarvis/docs/PHASE_1_1.md`.
Branche de dev : `claude/build-jarvis-ecosystem-vSyeD`.

## Règles de travail (mémo Laurent)

1. **Essayer avant de refuser.** Si je peux tenter une connexion, un outil, ou
   un bypass via ce qui est dispo (ex : `claude` CLI déjà authentifié au lieu
   de réclamer une clef API brute), je le tente d'abord. Je n'attends pas une
   autorisation. Autonomie > prudence excessive.
2. **Ne jamais commit `.env`** — git-ignored. Secrets locaux seulement.
3. **Jamais citer "Sika" ni "Parexlanko"** dans les réponses Jarvis
   (le scope filter bloque de toute façon).
4. **Reporter au format imposé** (🟢📦🧪💶📈⏭️❓) à chaque jalon.
5. **Voice DNA** : sympa, cool, dynamique, compréhensif, pro. Zéro phrase
   bannie FR. Voice lint exécuté avant chaque envoi.

## État actuel (Phase 1.2)

- Bot Telegram `@Jarvisjonction_bot` tourne, whitelist user 5202321140
- SQLite persistance locale (bus, queue, memory, audit)
- Pipeline Jarvis : Router → Planner → Dispatcher → Aggregator → Verifier
- Builder v1 écrit des spécialistes sur disque
- ConversationOrchestrator, Compliance, voice lint opérationnels
- **LLM backend** : `claude` CLI local (OAuth Claude Code) quand pas de clef
  Anthropic brute. Fallback stub déterministe.

## Commandes utiles

```bash
cd jarvis/
PYTHONPATH=. python3 -m pytest tests/              # tests
set -a && . ./.env && set +a && \
  PYTHONPATH=. nohup python3 -m jarvis.telegram_bot.bot \
  > logs/telegram.log 2>&1 &                       # démarrer bot
pgrep -af jarvis.telegram_bot.bot                  # vérifier
pkill -f jarvis.telegram_bot.bot                   # arrêter
tail -f logs/telegram.log                          # logs bot
tail -f logs/audit.jsonl                           # audit trail
```

## Prochaines priorités

- Brancher le LLM via CLI au pipeline Jarvis → réponses réellement
  intelligentes sur /plan, CLARIFY, etc.
- Quand Laurent fournit `ANTHROPIC_API_KEY` brute + `ANTHROPIC_ZDR=true` →
  basculer au SDK natif (moins cher, plus contrôle).
- Supabase : skippé pour l'instant, SQLite suffit.
