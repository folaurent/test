---
description: Exécute un cycle de gestion complet (dry-run par défaut).
---

Exécute un cycle de gestion complet (dry-run par défaut).

Exécute depuis la racine `company/` :

```bash
python orchestrator/orchestrator.py --cycle --dry-run
```

Puis résume à l'opérateur le résultat (initiatives, file d'approbation,
compteur d'exclusion de données = 0, alertes budget). Respecte la Constitution
(`CLAUDE.md`) : aucune action ROUGE n'est exécutée sans approbation humaine.
