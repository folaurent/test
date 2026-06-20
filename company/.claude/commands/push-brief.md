---
description: Envoie le dernier brief CEO sur Slack/Telegram (notification à la demande).
---

Pousse le brief exécutif CEO sur le canal de l'opérateur (Slack/Telegram).

```bash
python orchestrator/orchestrator.py --push-brief
```

Prérequis : `SLACK_WEBHOOK_URL` (ou `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`)
défini dans l'environnement ou dans `company/.env` (chargé automatiquement).

C'est une notification **AMBRE** (informative, réversible) vers ton propre
canal — elle s'envoie à la demande, indépendamment du mode dry-run/live, et
est journalisée dans l'`audit_log`. Elle n'exécute aucune action ROUGE.
