# Portail Client — Interface d'automatisations

> Spécification & architecture — v0.1 (session de cadrage)

## 1. Vision

Une application web où l'agence **onboarde ses clients** et leur propose un
**catalogue d'automatisations**. Le client déclenche une automatisation depuis
l'interface ; le déclenchement appelle un **webhook n8n** (ou, plus tard, du code
custom) qui exécute la logique métier en backend et renvoie un statut/résultat.

Décisions de cadrage validées :

| Sujet              | Choix retenu                                                        |
| ------------------ | ------------------------------------------------------------------- |
| Modèle d'accès     | Agence (admin) + clients cloisonnés (multi-tenant)                  |
| Stack              | Next.js (App Router) + Supabase (Auth, Postgres, RLS)               |
| Déclenchement      | Webhooks n8n (1 workflow par automatisation), extensible au code    |
| Première étape     | Specs + architecture, puis MVP                                      |

À confirmer / paramètres ouverts (voir §9) : volumétrie, types de déclencheurs
(à la demande / planifié / événementiel), besoin d'historique côté client.

## 2. Personae & rôles

- **Owner / Admin agence** : voit tous les clients (organisations), gère le
  catalogue d'automatisations, attribue les automatisations à chaque client,
  consulte les logs d'exécution.
- **Membre client (org_admin / member)** : ne voit que **son** organisation,
  son catalogue attribué, lance les automatisations et consulte son historique.

Le cloisonnement est porté par l'**organisation** (= un client). Un utilisateur
appartient à une organisation via la table `memberships`. L'agence est une
organisation spéciale avec le flag `is_agency = true`.

## 3. Architecture cible

```
┌─────────────┐     HTTPS      ┌──────────────────────┐
│  Navigateur │ ─────────────► │  Next.js (App Router) │
│  (client)   │ ◄───────────── │  - UI / pages         │
└─────────────┘                │  - Route handlers API │
                               │  - Server Actions     │
                               └─────────┬────────────┘
                                         │ service-role (server only)
                                         ▼
                               ┌──────────────────────┐
                               │      Supabase         │
                               │  Auth · Postgres+RLS  │
                               └─────────┬────────────┘
                                         │ insert run (queued)
                                         ▼
                               ┌──────────────────────┐
   signature HMAC + secret     │  Déclencheur backend  │
   ┌──────────────────────────►│  n8n webhook / code   │
   │   POST /webhook/<auto>     └─────────┬────────────┘
   │                                      │ callback (statut/résultat)
   └──────────────────────────────────────┘
            POST /api/runs/<id>/callback (signé)
```

Points clés :

1. Le navigateur ne parle **jamais** directement à n8n. Il appelle une route
   Next.js côté serveur, qui valide les droits (l'automatisation est-elle bien
   attribuée à l'org de l'utilisateur ?) avant de relayer vers n8n.
2. Le secret du webhook n8n et la `service_role` Supabase restent **côté
   serveur uniquement**.
3. n8n notifie la fin d'exécution via un **callback signé** qui met à jour la
   ligne `automation_runs` (statut, résultat, logs).

## 4. Modèle de données (Postgres / Supabase)

```sql
-- Organisations = clients (+ l'agence elle-même)
organizations (
  id uuid pk,
  name text,
  is_agency boolean default false,
  created_at timestamptz default now()
)

-- Lien utilisateur Supabase <-> organisation + rôle
memberships (
  id uuid pk,
  user_id uuid references auth.users,
  org_id uuid references organizations,
  role text check (role in ('owner','org_admin','member')),
  unique (user_id, org_id)
)

-- Catalogue : défini une fois par l'agence
automations (
  id uuid pk,
  slug text unique,              -- ex: "enrich-leads"
  name text,
  description text,
  icon text,
  trigger_type text check (trigger_type in ('on_demand','scheduled','event')),
  webhook_url text,              -- endpoint n8n (jamais exposé au client)
  input_schema jsonb,            -- champs du formulaire de lancement
  is_active boolean default true,
  created_at timestamptz default now()
)

-- Attribution d'une automatisation à un client
org_automations (
  id uuid pk,
  org_id uuid references organizations,
  automation_id uuid references automations,
  enabled boolean default true,
  config jsonb,                  -- valeurs spécifiques au client (clés API, etc.)
  unique (org_id, automation_id)
)

-- Historique d'exécution
automation_runs (
  id uuid pk,
  org_id uuid references organizations,
  automation_id uuid references automations,
  triggered_by uuid references auth.users,
  status text check (status in ('queued','running','success','error')),
  input jsonb,
  output jsonb,
  error text,
  created_at timestamptz default now(),
  finished_at timestamptz
)
```

### Sécurité (RLS)

- `organizations`, `memberships`, `org_automations`, `automation_runs` :
  un utilisateur ne lit que les lignes de **ses** organisations
  (`org_id in (select org_id from memberships where user_id = auth.uid())`).
- L'agence (`is_agency`) bypass via une policy dédiée pour l'admin.
- `automations.webhook_url` n'est **jamais** servi au client : l'API n'expose
  que les champs publics (`slug`, `name`, `description`, `input_schema`).
- Les écritures sensibles (création de run, callback n8n) passent par des
  route handlers serveur utilisant la `service_role`, pas le client.

## 5. Flux de déclenchement (on-demand)

1. Le client ouvre une automatisation → formulaire généré depuis `input_schema`.
2. Soumission → `POST /api/automations/<slug>/run` (route serveur).
3. La route vérifie : user authentifié, org possède `org_automations.enabled`.
4. Insertion `automation_runs (status='queued', input=...)`.
5. La route POST le webhook n8n avec un payload signé (HMAC) incluant
   `run_id`, `org_id`, `input`, et l'`org_automations.config`.
6. n8n exécute, puis appelle `POST /api/runs/<run_id>/callback` (signé) →
   `status='success'|'error'`, `output`, `finished_at`.
7. L'UI suit le statut (polling court ou Supabase Realtime sur `automation_runs`).

## 6. Écrans (MVP)

**Espace client**
- `/login` — auth Supabase (email magic link ou password)
- `/` — dashboard : cartes des automatisations attribuées + statut
- `/automations/[slug]` — détail + formulaire de lancement
- `/runs` — historique des exécutions de l'org
- `/runs/[id]` — détail d'un run (input, output, logs, statut)

**Espace agence (admin)**
- `/admin/orgs` — liste des clients, création, invitations
- `/admin/automations` — CRUD du catalogue (slug, webhook, input_schema)
- `/admin/orgs/[id]` — attribution des automatisations à un client + config
- `/admin/runs` — tous les runs, debugging

## 7. Stack technique détaillée

- **Next.js 14+ (App Router, TypeScript)** — UI + route handlers + server actions
- **Supabase** — Auth, Postgres, RLS, Realtime, Storage (fichiers générés)
- **UI** : Tailwind CSS + shadcn/ui (composants accessibles, rapides à poser)
- **Validation** : Zod (côté serveur sur tous les inputs)
- **Déploiement** : Vercel (front + API) ; n8n hébergé séparément (cloud ou self-host)
- **Secrets** : variables d'env Vercel ; jamais dans le bundle client

## 8. Découpage en lots (proposé)

- **Lot 0 — Scaffolding** : projet Next.js + Tailwind + connexion Supabase + auth.
- **Lot 1 — Multi-tenant** : tables, RLS, memberships, login, garde d'accès.
- **Lot 2 — Catalogue & attribution** : admin CRUD automations + attribution org.
- **Lot 3 — Déclenchement** : run on-demand → webhook n8n + callback signé.
- **Lot 4 — Historique** : liste/détail des runs, statut temps réel.
- **Lot 5 — Onboarding** : invitations clients, branding par org.

## 9. Questions ouvertes (à trancher avant Lot 3)

1. **Volumétrie** court terme (nb clients × nb automatisations) → niveau de robustesse.
2. **Types de déclencheurs** dominants : bouton à la demande / planifié / événementiel ?
   Un exemple concret d'automatisation à offrir.
3. **Historique côté client** : besoin de logs/fichiers/statut visibles, ou juste
   « cliquer et c'est traité ailleurs » ?
4. **n8n** : instance cloud n8n.io ou self-hosted ? (impacte l'auth des webhooks)
5. **Auth client** : magic link (sans mot de passe) ou email + mot de passe ?
