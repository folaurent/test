---
description: Dialogue — l'agent CEO répond naturellement à un message et agit sur vos décisions.
---

Fais dialoguer l'agent CEO avec l'opérateur : il répond naturellement (comme un
dirigeant humain), en s'appuyant sur l'état réel, et exécute les arbitrages
explicites contenus dans le message.

```bash
python orchestrator/orchestrator.py --reply "$ARGUMENTS"
```

Exemples :
- `/reply "ok pour #1, mais explique-moi pourquoi le SEO d'abord"` → valide la
  décision #1 puis répond.
- `/reply "rejette #2, trop tôt pour publier"` → rejette #2 et explique la suite.

L'agent décide AVEC toi : il propose et demande, n'exécute aucune action ROUGE
sans ton accord explicite. Réponse en LLM (Claude) si `ANTHROPIC_API_KEY` est
défini, sinon repli naturel ancré sur l'état réel. Envoi Slack + journalisé.
