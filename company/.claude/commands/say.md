---
description: L'agent envoie un message libre à l'opérateur sur Slack/Telegram.
---

Fais parler l'agent CEO à l'opérateur sur son canal Slack/Telegram.

```bash
python orchestrator/orchestrator.py --say "$ARGUMENTS"
```

Prérequis : `SLACK_WEBHOOK_URL` (ou Telegram) dans l'environnement ou `company/.env`.

Notification **AMBRE** (informative, réversible), journalisée dans l'`audit_log`.
N'exécute aucune action ROUGE. Pour pousser le brief complet, voir `/push-brief` ;
les alertes de fin de cycle s'activent avec `COMPANY_SLACK_ALERTS=1`.
