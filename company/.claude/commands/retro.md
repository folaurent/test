---
description: Force une rétrospective (relance ADAPT via un cycle).
---

Force une rétrospective (relance ADAPT via un cycle).

Exécute depuis la racine `company/` :

```bash
python orchestrator/orchestrator.py --cycle --dry-run
```

Puis résume à l'opérateur le résultat (initiatives, file d'approbation,
compteur d'exclusion de données = 0, alertes budget). Respecte la Constitution
(`CLAUDE.md`) : aucune action ROUGE n'est exécutée sans approbation humaine.
