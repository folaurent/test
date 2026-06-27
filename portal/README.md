# Portail Client — Automatisations

Portail multi-tenant où l'agence onboarde ses clients et leur propose un
catalogue d'automatisations déclenchables en un clic (backend n8n / code).

- **Stack** : Next.js (App Router) + Supabase (Auth/Postgres/RLS) + n8n webhooks
- **Architecture & specs** : voir [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## État

🟡 Cadrage en cours — voir le découpage en lots (§8) et les questions
ouvertes (§9) dans le document d'architecture.

## Prochaines étapes

1. Valider les questions ouvertes (§9).
2. Lot 0 — scaffolding Next.js + Supabase + auth.
3. Lot 1 — multi-tenant (tables, RLS, login).
