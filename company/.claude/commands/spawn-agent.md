---
description: Invoque l'Agent Factory. Usage: /spawn-agent "<besoin>".
---

Invoque l'Agent Factory. Usage: /spawn-agent "<besoin>".

Exécute depuis la racine `company/` :

```bash
python orchestrator/orchestrator.py --spawn-agent "$ARGUMENTS"
```

Puis résume à l'opérateur le résultat (initiatives, file d'approbation,
compteur d'exclusion de données = 0, alertes budget). Respecte la Constitution
(`CLAUDE.md`) : aucune action ROUGE n'est exécutée sans approbation humaine.
