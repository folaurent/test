---
description: Injecte une idée dans l'INTAKE. Usage: /new-initiative "<idée>".
---

Injecte une idée dans l'INTAKE. Usage: /new-initiative "<idée>".

Exécute depuis la racine `company/` :

```bash
python orchestrator/orchestrator.py --new-initiative "$ARGUMENTS"
```

Puis résume à l'opérateur le résultat (initiatives, file d'approbation,
compteur d'exclusion de données = 0, alertes budget). Respecte la Constitution
(`CLAUDE.md`) : aucune action ROUGE n'est exécutée sans approbation humaine.
