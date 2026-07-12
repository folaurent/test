---
description: Désactive le kill switch (STATE=RUNNING).
---

Désactive le kill switch (STATE=RUNNING).

Exécute depuis la racine `company/` :

```bash
python orchestrator/orchestrator.py --resume
```

Puis résume à l'opérateur le résultat (initiatives, file d'approbation,
compteur d'exclusion de données = 0, alertes budget). Respecte la Constitution
(`CLAUDE.md`) : aucune action ROUGE n'est exécutée sans approbation humaine.
