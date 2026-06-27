# Portail Client — Automatisations

Portail multi-tenant où l'agence onboarde ses clients et leur propose un
catalogue d'automatisations déclenchables en un clic (backend n8n / code).

- **Stack** : Next.js (App Router) + Supabase (Auth/Postgres/RLS) + n8n webhooks
- **Architecture & specs** : voir [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## Maquette interactive (pour le développeur)

Une **maquette cliquable** (façon Lovable) sert de spec visuelle : elle montre
les écrans, les interactions et les flux attendus, **sans backend**.

```
portal/prototype/   →  ouvrir index.html dans un navigateur
```

- Données fictives, aucune dépendance, aucun build.
- Bouton **Client / Agence** en haut pour basculer entre les deux espaces.
- Écrans : login (magic link), tableau de bord client, détail + config d'une
  automatisation, historique des exécutions, console agence (clients, catalogue,
  attribution avec jeton d'ingestion).

> À donner au développeur **avec** `docs/ARCHITECTURE.md` : la maquette dit
> *quoi*, le document dit *comment*.

## État

🟡 Cadrage + maquette faits. Reste : implémentation réelle (Lots 0→5).

## Prochaines étapes

1. Le dev s'appuie sur la maquette + l'archi pour estimer.
2. Lot 0 — scaffolding Next.js + Supabase + auth magic link.
3. Lot 1 — multi-tenant (tables, RLS, login).
