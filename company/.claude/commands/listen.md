---
description: Dialogue autonome — l'agent lit les nouveaux messages Slack et y répond.
---

L'agent lit les nouveaux messages de l'opérateur sur Slack et y répond tout seul
(une passe : idéal en cron pour un dialogue continu).

```bash
python orchestrator/orchestrator.py --listen
```

Prérequis : `SLACK_BOT_TOKEN` (scope `channels:history`) + `SLACK_CHANNEL_ID`
dans l'environnement ou `company/.env`. L'incoming webhook seul ne permet que
d'écrire ; lire nécessite un bot Slack ajouté au canal.

Pour chaque message humain depuis la dernière passe, l'agent répond naturellement
et exécute les arbitrages explicites (« ok pour #3 »). Le curseur de lecture est
mémorisé dans `state/slack_last_ts`. Aucune action ROUGE sans accord explicite.
