# 🏢 Entreprise IA pilotée par un Agent CEO autonome

Un système multi-agents où un **Agent CEO** dirige une activité e-commerce /
contenu : il idée, analyse, décide, délègue à des agents spécialisés (qu'il peut
**recruter lui-même** via l'Agent Factory), mesure, s'auto-corrige et reporte —
le tout **sous garde-fous stricts**, avec l'humain dans la boucle sur les
actions à conséquence.

> ⚠️ **Par défaut, tout tourne en `--dry-run` : aucun effet de bord externe.**
> Aucune action ROUGE (argent, légal, publication, envoi réel, suppression)
> n'est jamais exécutée sans approbation humaine.

---

## Démarrage rapide

```bash
cd company

# 1. Initialiser la base d'état + synchroniser les agents
python orchestrator/orchestrator.py --bootstrap

# 2. Lancer un cycle de gestion complet (dry-run)
python orchestrator/orchestrator.py --cycle --dry-run

# 3. Lire le brief CEO généré
ls reports/        # le dernier .md
```

Aucune dépendance externe : **Python 3 (stdlib uniquement)**.

---

## Slash commands (Claude Code)

| Commande | Effet |
|----------|-------|
| `/bootstrap` | Scaffold / synchronisation des agents |
| `/run-cycle` | Un cycle de gestion complet (dry-run) |
| `/new-initiative "<idée>"` | Injecte une idée dans l'INTAKE |
| `/spawn-agent "<besoin>"` | Invoque l'Agent Factory |
| `/ceo-brief` | (Re)génère le brief exécutif |
| `/retro` | Force une rétrospective |
| `/approve <id>` · `/reject <id>` | Résout la file d'approbation |
| `/pause` · `/resume` | Bascule le kill switch |
| `/org` | Organigramme, registre d'agents, KPI |

Équivalents CLI : `python orchestrator/orchestrator.py --<commande>`.

---

## La boucle d'orchestration (un cycle)

```
0. CHECK    → si STATE == PAUSED, arrêt immédiat
1. INTAKE   → idées CEO + items en attente (filtre exclusions, verrou 1)
2. TRIAGE   → Chief of Staff score (impact×effort×risque) et route
3. PLAN     → CEO sélectionne, fixe KPI, alloue le budget cycle
4. DISPATCH → assigne aux agents ; compétence manquante → Agent Factory
5. EXECUTE  → livrables dans /artifacts ; chaque action passe par guardrails
6. REVIEW   → quality-retro + CEO contrôlent
7. MEASURE  → metrics vs cibles
8. ADAPT    → leçons → playbook ; re-score des agents
9. REPORT   → brief CEO + file d'approbation
```

Le cycle est **idempotent et reprenable** : tout l'état vit dans
`state/company.db` et `/artifacts`. Une nouvelle invocation reprend le fil.

---

## Garde-fous

- **Taxonomie VERT / AMBRE / ROUGE** classée *avant* toute action
  (`orchestrator/guardrails.py`). Un signal ROUGE ne peut jamais être déclassé.
- **Double verrou d'exclusion de données** (Sika, Parexlanko) : à l'INTAKE et
  avant chaque action. Compteur cible = **0** (toute tentative est comptée +
  alertée).
- **Budget** : plafond cycle (10) + global (100), hard stop au dépassement.
- **Kill switch** : `state/STATE` = `PAUSED`.
- **Journal d'audit** exhaustif : table `audit_log`.

Lancer la suite de tests des garde-fous :

```bash
python tests_guardrails.py
```

---

## Exécution autonome (scheduling)

Claude Code n'est pas un serveur permanent : l'autonomie vient de **l'état
persistant + invocations planifiées**.

- **Manuel** : `/run-cycle` ou `python orchestrator/orchestrator.py --cycle`.
- **Continu** (exemple cron, un cycle par heure, headless) :

  ```cron
  0 * * * * cd /chemin/vers/company && claude -p "/run-cycle" >> state/cron.log 2>&1
  ```

  Ou directement : `python orchestrator/orchestrator.py --cycle --dry-run`.

Chaque exécution lit l'état depuis `company.db` et reprend où la précédente
s'est arrêtée.

### Reporting Slack / Telegram (optionnel)

Le brief peut être poussé sur Slack/Telegram (`orchestrator/notify.py`).
**Désactivé par défaut** ; activé seulement si les variables d'environnement
sont présentes **et** hors dry-run :

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
# ou
export TELEGRAM_BOT_TOKEN="..." ; export TELEGRAM_CHAT_ID="..."
```

En dry-run, `notify.py` journalise ce qui *serait* envoyé, sans appel réseau.

---

## Intégrations (LLM, Shopify, Slack)

Toutes les intégrations **dégradent proprement** : si la dépendance/clé est
présente et qu'on est en `--live`, elles font le travail réel ; sinon (ou en
`--dry-run`), elles retombent sur un repli déterministe simulé. Le dry-run
reste donc toujours sans effet de bord externe.

| Intégration | Module | Active si | Comportement par défaut |
|---|---|---|---|
| **LLM (Claude)** | `orchestrator/llm.py` | `ANTHROPIC_API_KEY` + SDK `anthropic` + `--live` | Stub déterministe (idéation depuis la banque) |
| **Shopify** | `orchestrator/connectors/shopify.py` | `SHOPIFY_STORE_DOMAIN` + `SHOPIFY_ADMIN_TOKEN` + `--live` | KPI simulés |
| **Slack/Telegram** | `orchestrator/notify.py` | webhook/token présents + `--live` | Brief en fichier seul |

Cognition LLM réelle (mode `--live`) :

```bash
pip install -r requirements.txt          # installe le SDK anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
export COMPANY_LLM_MODEL="claude-opus-4-8"   # optionnel (défaut)
```

Un appel LLM est classé **AMBRE** : son coût estimé est imputé au budget
(cycle + global) et journalisé dans l'`audit_log`. Hard stop si le plafond
serait dépassé.

Données e-commerce réelles (Shopify, **lecture seule**) :

```bash
export SHOPIFY_STORE_DOMAIN="ma-boutique.myshopify.com"
export SHOPIFY_ADMIN_TOKEN="shpat_..."
```

Le connecteur n'écrit jamais. Toute écriture (créer un produit, changer un
prix, lancer une promo) reste une action **ROUGE** → file d'approbation.

**Pont MCP (complément interactif).** Quand le cycle est piloté par **Claude
Code**, les outils **Shopify MCP** peuvent récupérer des données que l'API
Admin headless ne fournit pas (sessions, taux de conversion). Le flux :

1. Claude Code appelle le Shopify MCP (`get-shop-info`, `run-analytics-query`…).
2. Il écrit `state/shopify_signals.json` (schéma : `state/shopify_signals.example.json`).
3. L'orchestrateur lit ce fichier **en priorité** (ingéré > API live > simulé),
   **sans aucun appel réseau de sa part** — la récupération a déjà eu lieu côté
   agent. Le dry-run reste donc sans effet de bord.

Slash command dédiée : **`/ingest-shopify`**. Le fichier ingéré n'est pas
versionné (données propres à la boutique) ; seul le schéma d'exemple l'est.

Reporting Slack / Telegram :

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
# ou
export TELEGRAM_BOT_TOKEN="..." ; export TELEGRAM_CHAT_ID="..."
```

Vérifier l'état des intégrations à tout moment : `python orchestrator/orchestrator.py --org`.

---

## Passer du dry-run au réel

1. Faire tourner plusieurs cycles en `--dry-run` et **inspecter les briefs**.
2. Vérifier que le compteur d'exclusion reste à **0** et que les actions ROUGE
   sont bien mises en file.
3. Fournir les clés voulues (LLM, Shopify, Slack — voir ci-dessus).
4. **Autoriser explicitement le réel** (garde-fou de passage) :

   ```bash
   export COMPANY_ALLOW_LIVE=1
   python orchestrator/orchestrator.py --cycle --live
   ```

   Sans `COMPANY_ALLOW_LIVE=1`, `--live` est refusé. En réel, les dépenses
   AMBRE sous plafond deviennent effectives ; les actions ROUGE restent
   **toujours** en file d'approbation.
5. Brancher les connecteurs un par un, en vérifiant le brief à chaque étape.

---

## Arborescence

```
company/
  CLAUDE.md              # la Constitution (règles permanentes)
  README.md             # ce fichier
  tests_guardrails.py   # tests des garde-fous
  .claude/
    agents/             # 13 agents (roster initial) + agents créés par la Factory
    commands/           # slash commands
    hooks/              # hook de logging optionnel
  orchestrator/
    orchestrator.py     # la boucle (un cycle complet) + CLI
    guardrails.py       # VERT/AMBRE/ROUGE + plafonds + exclusions
    memory.py           # accès à l'état (SQLite)
    reporting.py        # brief CEO + tableau de bord
    factory.py          # Agent Factory (création dynamique d'agents)
    notify.py           # connecteur Slack/Telegram (off par défaut)
  state/
    schema.sql          # schéma de company.db
    company.db          # état persistant (généré, non versionné)
    STATE               # drapeau RUNNING | PAUSED
  artifacts/            # livrables des agents (par initiative)
  reports/              # briefs CEO horodatés
  playbook/
    lessons.md          # leçons apprises
    agent_scores.md     # scores des agents
```
