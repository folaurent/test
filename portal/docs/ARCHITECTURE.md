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
| Déclenchement      | **Événementiel** (événement externe → n8n), bouton à la demande en option |
| Volumétrie cible   | Moyen — 5 à 20 clients (multi-tenant et logs soignés dès le départ) |
| Historique client  | Statut simple (queued/running/success/error), sans logs détaillés ni fichiers |
| Infra              | n8n **cloud** (n8n.io) ; auth client par **magic link** (sans mot de passe) |
| Première étape     | Specs + architecture, puis MVP                                      |

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
  Événement externe                ┌──────────────────────┐
  (lead, email, paiement…) ───────►│  n8n (cloud)          │
                                    │  workflow / trigger   │
   (option) POST /webhook/<auto>    └─────────┬────────────┘
   signé HMAC, depuis le portail              │ POST /api/ingest
                                              │ (signé, ingest_token)
                                              ▼
                                    enregistre/MAJ automation_runs
                                    → statut visible côté client (Realtime)
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
  ingest_token text unique,      -- secret de rattachement événement n8n -> org
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

## 5. Flux de déclenchement

### 5.1 Événementiel (flux principal)

L'exécution part d'un **événement externe** (nouveau lead, email reçu, paiement…)
qui arrive d'abord dans n8n. Le portail n'initie pas le run : il l'**enregistre**
et en montre le **statut** au bon client.

Enjeu clé : n8n doit savoir **à quel client (org)** rattacher l'événement. Pour
ça, chaque attribution `org_automations` possède un **token d'ingestion unique**
(`ingest_token`). n8n inclut ce token (ou l'utilise dans l'URL de callback) pour
identifier l'org.

1. Un événement externe atteint le workflow n8n (trigger n8n natif ou webhook entrant).
2. n8n traite, puis notifie le portail :
   `POST /api/ingest` avec un payload **signé (HMAC)** contenant
   `ingest_token`, `status`, et un `output` minimal.
3. Le portail résout `ingest_token → (org_id, automation_id)`, vérifie
   `org_automations.enabled`, puis crée/MAJ une ligne `automation_runs`
   (`status` = `running` puis `success`/`error`, `finished_at`).
4. Côté client, l'UI affiche le statut en quasi temps réel
   (Supabase Realtime sur `automation_runs`, filtré par org via RLS).

Le client, lui, **active/désactive** et **configure** ses automatisations depuis
l'app ; il n'a pas besoin de cliquer pour déclencher.

### 5.2 À la demande (option, bouton)

Conservé pour les automatisations qu'un client veut lancer manuellement :

1. Le client ouvre une automatisation → formulaire généré depuis `input_schema`.
2. `POST /api/automations/<slug>/run` (route serveur) vérifie auth + `enabled`.
3. Insertion `automation_runs (status='queued')`, puis POST signé au webhook n8n.
4. n8n exécute et notifie via le même endpoint `/api/ingest` (statut final).

> Statut simple retenu : on stocke `status`/`finished_at` et un `output` léger.
> Pas de logs détaillés ni de fichiers générés exposés au client pour le MVP.

## 6. Écrans (MVP)

**Espace client**
- `/login` — auth Supabase par **magic link** (sans mot de passe)
- `/` — dashboard : cartes des automatisations attribuées, **toggle actif/inactif**,
  dernier déclenchement et statut
- `/automations/[slug]` — détail + configuration (champs `config`) + bouton
  « lancer maintenant » si l'automatisation l'autorise
- `/runs` — flux des exécutions de l'org (statut simple)
- `/runs/[id]` — détail d'un run (statut, horodatage, output léger)

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

## 8b. Automatisation interactive — Outreach Engine (OpenOutreach)

Certaines automatisations ne sont pas de simples toggles : elles sont
**interactives** et ont leurs propres écrans. La première est l'**Outreach
Engine**, branchée sur [OpenOutreach](https://github.com/eracle/OpenOutreach)
(prospection B2B LinkedIn + email, pipeline IA/ML, mini-CRM).

Voir la maquette : `prototype/` → carte « Outreach Engine » (route `#/outreach`).

**Ce que le client fait depuis le portail**
- Onglet **Targeting & criteria** : il saisit ses critères (ce qu'il vend, ICP —
  intitulés, secteurs, taille, zones, mots-clés —, canaux, ton, modèles de
  message, nombre de relances, limites quotidiennes, rigueur de qualification),
  puis clique **Launch campaign**.
- Onglet **Pipeline** : funnel Discovered → Qualified → Contacted → Replied →
  Meetings, stats et activité du jour (dans les limites de sécurité).
- Onglet **Leads** : mini-CRM (poste, société, canal, stage, fit score).
- Onglet **Inbox** : fil de conversation géré par l'IA, reprise manuelle possible.

**Côté intégration (pour le dev)**
- `Launch campaign` → `POST /api/automations/outreach-engine/run` (route serveur
  signée) avec le payload de critères → webhook n8n qui pilote l'instance
  OpenOutreach du client (1 instance / déploiement isolé par org recommandé).
- OpenOutreach renvoie l'avancement via `/api/ingest` (signé, `ingest_token`) :
  nouveaux leads, changements de stage, réponses entrantes → le portail met à
  jour le funnel, la table des leads et l'inbox (Supabase Realtime).
- Tables additionnelles : `outreach_campaigns` (critères + statut),
  `outreach_leads` (lead, stage, score, canal), `outreach_messages` (fil).
- Secrets (LinkedIn, clé LLM, email-finder, mailbox) restent côté serveur /
  instance OpenOutreach — jamais exposés au client. Le portail n'affiche que des
  **statuts de connexion** (panneau « Connections »).

## 9. Décisions de cadrage (tranchées)

1. **Volumétrie** : 5 à 20 clients → multi-tenant et logs soignés dès le départ,
   sans sur-ingénierie (pas de file d'attente dédiée pour l'instant).
2. **Déclencheurs** : **événementiel** en flux principal (§5.1), bouton à la
   demande gardé en option (§5.2).
3. **Historique côté client** : **statut simple** (queued/running/success/error
   + horodatage + output léger). Pas de logs détaillés ni de fichiers au MVP.
4. **n8n** : instance **cloud** (n8n.io).
5. **Auth client** : **magic link** Supabase (sans mot de passe).

### Reste à préciser (n'empêche pas de démarrer)

- Un **exemple concret** d'automatisation réelle à offrir (pour modéliser le
  premier workflow n8n de bout en bout).
- Le besoin éventuel d'**invitations multi-membres** côté client (rôles).
