# PROMPT — Agent CEO Autonome (à coller dans Claude Code à la racine d’un dépôt vide)

## RÔLE

Tu es l’**architecte principal** d’un système multi-agents autonome. Ta mission : construire de A à Z une « entreprise pilotée par IA » dont le cœur est un **Agent CEO** qui dirige toute la société sans intervention humaine au quotidien. Le CEO génère des idées, les analyse, décide, délègue à une équipe d’agents spécialisés **qu’il recrute lui-même**, mesure les résultats, et s’auto-corrige.

Tu travailles **par phases**. Tu vérifies chaque phase avant de continuer et tu t’arrêtes aux points 🚦 pour me demander validation. **Réfléchis longuement (think hard) avant chaque phase de conception** : c’est un système qui agira de façon autonome, l’architecture et les garde-fous priment sur la vitesse.

-----

## 0. PRINCIPES DIRECTEURS (non négociables)

1. **Humain dans la boucle sur les actions à conséquence.** Toute action irréversible, coûteuse, légale, ou tournée vers le monde réel (mouvement d’argent, email à un vrai client, publication, signature, suppression de données) **n’est jamais exécutée automatiquement** : elle est mise en file d’attente d’approbation.
1. **Tout est journalisé.** Chaque décision et chaque action passent par un `audit_log` horodaté et traçable.
1. **Budget plafonné.** Un plafond par cycle et un plafond global, avec arrêt dur (hard stop) au dépassement.
1. **Kill switch.** Un état `PAUSED` que la boucle vérifie en tout premier ; si activé, rien ne s’exécute.
1. **Exclusion de données stricte.** Les entités **Sika** et **Parexlanko** (et toute entité listée dans `data_exclusions`) ne doivent **jamais** être ingérées, traitées ou référencées par aucun agent. Double verrou : (1) filtre en entrée, (2) contrôle avant chaque action. Le compteur du tableau de bord doit rester à **0**.
1. **Pas de fabrication.** Les agents citent leurs sources ou marquent explicitement leurs hypothèses. Une incertitude se déclare, elle ne s’invente pas.
1. **Déterminisme et transparence.** Privilégie les workflows déterministes et auditables. Tout comportement non déterministe (appel LLM) doit produire une trace exploitable.
1. **Construction incrémentale + vérification.** Chaque brique est testée avant d’enchaîner.

-----

## 1. VISION DU CEO AGENT

Le CEO est un orchestrateur stratégique, pas un exécutant. Son cycle de vie mental :

- **Idéation** — il génère des hypothèses d’amélioration / croissance à partir de l’état de l’entreprise, des signaux disponibles et des dossiers en attente.
- **Analyse** — il évalue impact attendu × effort × risque, et priorise.
- **Décision** — il choisit les initiatives à lancer, alloue les ressources, fixe les objectifs et les KPI.
- **Délégation** — il dispatche aux agents spécialisés ; s’il manque une compétence, il **fait créer un nouvel agent** par l’Agent Factory.
- **Mesure** — il confronte les résultats aux KPI.
- **Adaptation** — il tire des leçons, ajuste la stratégie, fait réviser ou remplacer les agents sous-performants.
- **Reporting** — il produit un brief exécutif et remonte à l’humain ce qui requiert un arbitrage.

-----

## 2. ARCHITECTURE CIBLE

```
                          ┌─────────────────────────┐
        Humain  ◀────────▶│   AGENT CEO (stratégie) │
   (approbations,         └────────────┬────────────┘
    arbitrages,                        │
    pause/resume)            ┌─────────▼──────────┐
                             │  Chief of Staff    │  ← triage + routage
                             │  (router/dispatch) │
                             └─────────┬──────────┘
            ┌───────────────┬─────────┼─────────┬───────────────┐
            ▼               ▼         ▼         ▼               ▼
        Stratégie       Produit/   Growth/   Finance/        Operations
        & Research      R&D        Marketing Controlling      & Quality
            │               │         │         │               │
            └──────┬────────┴────┬────┴────┬────┴───────┬───────┘
                   ▼             ▼         ▼            ▼
              Sales/BizDev   Engineering  Legal/    Data/Analytics
                                          Compliance
                   │
                   ▼
          ┌────────────────────┐
          │   AGENT FACTORY    │  ← crée de NOUVEAUX agents à la demande
          │   (méta-agent)     │
          └────────────────────┘

   Socle transverse : Mémoire/État partagé · File de décisions/approbations ·
   Registre KPI · Journal d'audit · Garde-fous · Playbook (leçons)
```

**Roster initial d’agents** (chacun défini dans `.claude/agents/`) :
`chief-of-staff`, `strategy-research`, `product-rnd`, `engineering`, `growth-marketing`, `sales-bizdev`, `finance-controlling`, `operations`, `legal-compliance`, `people-recruiter`, `data-analytics`, `quality-retro` (agent d’auto-amélioration), et `agent-factory` (méta-agent).

-----

## 3. ARBORESCENCE DU PROJET

```
/company
  CLAUDE.md                  # la "Constitution" (contexte + règles permanentes)
  /.claude
    /agents                  # une définition par agent (markdown + frontmatter)
    /commands                # slash commands (voir §13)
    /hooks                   # hooks de logging / garde-fous
  /orchestrator
    orchestrator.py          # exécute UN cycle de gestion complet
    guardrails.py            # classification VERT/AMBRE/ROUGE + plafonds + exclusions
    memory.py                # accès à l'état (DB)
    reporting.py             # génération du brief CEO + tableau de bord
  /state
    company.db               # SQLite (état persistant) — voir §8
    STATE                    # fichier drapeau : RUNNING | PAUSED
  /artifacts                 # livrables produits par les agents (par initiative)
  /reports                   # briefs CEO horodatés
  /playbook
    lessons.md               # leçons apprises (croît au fil des cycles)
    agent_scores.md          # scores de performance des agents
  README.md                  # mode d'emploi opérateur
```

-----

## 4. LA CONSTITUTION (`CLAUDE.md`)

Rédige-la pour qu’elle serve de contexte permanent à toutes les sessions. Elle contient :

- **Mission et domaine de l’entreprise** (à définir avec moi en Phase 0).
- **Les 8 principes directeurs** du §0, en version exécutable.
- **L’organigramme** et le rôle de chaque agent.
- **La taxonomie d’actions** VERT/AMBRE/ROUGE (§10).
- **Les plafonds budgétaires** courants.
- **La liste d’exclusion de données** (Sika, Parexlanko + extensible).
- **Le protocole d’escalade** vers l’humain.
- **Les KPI de l’entreprise** et leurs cibles.

-----

## 5. DÉFINITION DES AGENTS (`.claude/agents/`)

Chaque agent suit ce gabarit (frontmatter + corps) :

```markdown
---
name: <slug>
role: <intitulé clair>
mission: <ce que l'agent accomplit, en une phrase>
triggers: <quand le Chief of Staff doit l'invoquer>
inputs: <ce qu'il attend en entrée>
tools: <outils/commandes autorisés — liste blanche>
deliverables: <ce qu'il produit, et où il le dépose>
success_criteria: <KPI mesurables de réussite>
escalation_rules: <ce qu'il remonte au CEO / à l'humain>
max_budget: <plafond de l'agent>
action_class: <classe par défaut des actions de l'agent>
---

Persona, méthode de travail, format de sortie, contraintes.
Rappel des principes directeurs et de l'exclusion de données.
```

Crée le roster initial du §2 selon ce gabarit. `quality-retro` est l’agent qui anime l’auto-amélioration (§9). `chief-of-staff` est le seul à router ; les agents métier ne s’auto-saisissent pas.

-----

## 6. L’AGENT FACTORY (création dynamique d’agents)

C’est ce qui rend le CEO réellement autonome. Quand le CEO (via le Chief of Staff) détecte un **manque de compétence** pour traiter une initiative, il invoque `agent-factory` avec un besoin en langage naturel. La Factory :

1. Traduit le besoin en **spec d’agent** (le gabarit du §5).
1. Vérifie qu’aucun agent existant ne couvre déjà ce besoin (évite la prolifération).
1. Écrit un nouveau fichier `.claude/agents/<slug>.md` valide.
1. Enregistre l’agent dans la table `agents` (créé_par = `agent-factory`, score initial neutre).
1. Le rend immédiatement disponible au routage.

Garde-fou : **un nouvel agent ne peut hériter que de classes d’action VERT/AMBRE**. Toute capacité ROUGE est désactivée par défaut et nécessite mon approbation explicite.

-----

## 7. LA BOUCLE D’ORCHESTRATION (`orchestrator.py`)

Un cycle de gestion = ces étapes, exécutées dans l’ordre, chacune journalisée :

```
0. CHECK     — si STATE == PAUSED → arrêt immédiat.
1. INTAKE    — rassemble : idées du CEO + signaux dispo + items en attente.
2. TRIAGE    — Chief of Staff score chaque item (impact × effort × risque) et route.
3. PLAN      — CEO sélectionne les initiatives du cycle, fixe objectifs + KPI, alloue le budget.
4. DISPATCH  — assigne aux agents ; si compétence manquante → Agent Factory.
5. EXECUTE   — les agents produisent leurs livrables dans /artifacts. Toute action
               est classée (VERT/AMBRE/ROUGE) AVANT exécution par guardrails.py.
               ROUGE → mise en approvals_queue, jamais exécutée.
6. REVIEW    — quality-retro + CEO contrôlent les livrables (conformité, qualité).
7. MEASURE   — mise à jour de la table metrics vs cibles.
8. ADAPT     — rétrospective : leçons → playbook ; re-score des agents ;
               révision/remplacement des agents sous-performants.
9. REPORT    — génère le brief CEO + la file d'approbation pour l'humain.
```

Le cycle doit être **idempotent et reprenable** : tout l’état vit dans `company.db` et `/artifacts`, donc une nouvelle invocation reprend là où la précédente s’est arrêtée. Implémente un mode `--dry-run` qui simule tout sans aucun effet de bord externe (par défaut au premier lancement).

-----

## 8. MÉMOIRE & ÉTAT PARTAGÉ (SQLite par défaut)

Schéma minimal (adaptable vers Supabase/Postgres si je le demande) :

```sql
agents(id, name, role, mission, system_prompt_path, tools, status,
       created_by, created_at, performance_score)
initiatives(id, title, hypothesis, rationale, status, priority,
            owner_agent, expected_kpi, result, created_at, closed_at)
tasks(id, initiative_id, assigned_agent, description, status,
      output_ref, depends_on, created_at, done_at)
decisions(id, context, options, chosen, rationale, decided_by,
          action_class, requires_human, approved_by, status, created_at)
metrics(id, name, value, unit, target, period, recorded_at)
lessons(id, source_initiative, observation, learning, action_taken, created_at)
audit_log(id, actor_agent, action, payload, action_class, reversible, ts)
approvals_queue(id, decision_id, summary, risk_level, requested_at,
                status, resolved_at, resolved_by)
data_exclusions(id, forbidden_entity, attempted_access_count)  -- seed: Sika, Parexlanko (count=0)
```

-----

## 9. AUTO-AMÉLIORATION (agent `quality-retro`)

À l’étape ADAPT de chaque cycle :

- **Rétrospective** : qu’est-ce qui a marché / échoué, et pourquoi (faits, pas opinions).
- **Scoring des agents** : chaque agent reçoit un score basé sur l’atteinte de ses `success_criteria`. Mise à jour de `agents.performance_score` et de `playbook/agent_scores.md`.
- **Raffinement des prompts** : si un agent sous-performe de façon répétée, proposer une révision de sa définition (à valider à un seuil donné).
- **Playbook croissant** : chaque leçon réutilisable est ajoutée à `playbook/lessons.md` et réinjectée en contexte aux cycles suivants.
- **Remplacement** : un agent sous un seuil critique sur N cycles est mis en quarantaine et la Factory est sollicitée pour une refonte.

-----

## 10. GARDE-FOUS & ESCALADE (`guardrails.py`) — détaillé

**Taxonomie des actions** (classée AVANT exécution) :

- 🟢 **VERT** — réversible, interne, sans coût (analyse, brouillon, fichier local, calcul) → **autonome**.
- 🟡 **AMBRE** — réversible mais externe ou faible coût (appel API payant sous plafond, écriture en base de test) → **autonome dans le budget + journalisé**.
- 🔴 **ROUGE** — irréversible / coûteux / légal / communication vers de vraies personnes / mouvement d’argent / publication / suppression de données → **STOP**, mise en `approvals_queue`, exécution interdite sans mon approbation.

**Autres garde-fous :**

- Plafond budgétaire par cycle + global, suivi dans `metrics`, hard stop au dépassement.
- Kill switch via `/state/STATE` (`PAUSED` → la boucle s’arrête à l’étape 0).
- **Exclusion de données double verrou** : (1) tout INTAKE filtre les entités de `data_exclusions` ; (2) tout EXECUTE re-vérifie avant action. Toute tentative incrémente `attempted_access_count` ET déclenche une alerte. Cible : compteur = 0.
- Journal d’audit exhaustif (qui, quoi, classe d’action, réversible, quand).

-----

## 11. REPORTING & KPI (`reporting.py`)

À chaque cycle, génère dans `/reports/<horodatage>.md` un **brief CEO** contenant :

- État des initiatives (lancées / en cours / clôturées) et résultats vs KPI.
- Tableau de bord des metrics vs cibles.
- **File d’approbation** : décisions ROUGE en attente de mon arbitrage (avec contexte + options + recommandation).
- Nouveaux agents créés ce cycle.
- Top 3 leçons du cycle.
- Compteur d’exclusion de données (doit afficher 0).
- Alertes budget.

(Optionnel, si je l’active : pousser ce brief sur Slack/Telegram via un connecteur.)

-----

## 12. EXÉCUTION AUTONOME (scheduling — sois réaliste)

Claude Code n’est pas un serveur permanent : l’autonomie vient de **l’état persistant + invocations planifiées**.

- **Un cycle manuel** : commande `/run-cycle` (ou `python orchestrator/orchestrator.py --cycle`).
- **Continu** : un cron / launchd / nœud N8N déclenche, à intervalle régulier (ex. horaire ou quotidien), `claude -p "/run-cycle"` en mode headless. Chaque exécution lit l’état depuis `company.db` et reprend le fil.
- Documente cette mise en place dans le `README.md`, y compris comment basculer `--dry-run` → exécution réelle une fois la confiance établie.

-----

## 13. SLASH COMMANDS À CRÉER (`.claude/commands/`)

- `/bootstrap` — scaffold initial (one-shot).
- `/run-cycle` — un cycle de gestion complet.
- `/new-initiative "<idée>"` — injecte une idée dans l’INTAKE.
- `/spawn-agent "<besoin>"` — invoque l’Agent Factory.
- `/ceo-brief` — (re)génère le brief exécutif.
- `/retro` — force une rétrospective.
- `/approve <id>` · `/reject <id>` — résout la file d’approbation.
- `/pause` · `/resume` — bascule le kill switch.
- `/org` — affiche l’organigramme, le registre d’agents et les KPI.

-----

## 14. SÉQUENCE DE DÉMARRAGE (ce que tu fais maintenant)

**Phase 0 — Cadrage 🚦** : pose-moi les questions indispensables avant de coder :

- Quelle est la **mission/le domaine réel** de l’entreprise gérée par le CEO ? (sinon, propose un défaut et continue)
- Stack d’état : **SQLite** (défaut) ou Supabase/Postgres ?
- Plafonds budgétaires (par cycle / global) ?
- Scheduler souhaité (cron / N8N / manuel) ?
- Reporting : fichier seul (défaut) ou aussi Slack/Telegram ?
  Attends mes réponses.

**Phase 1** — Scaffold de l’arborescence (§3) + schéma DB (§8) + seed de `data_exclusions` (Sika, Parexlanko).

**Phase 2** — Rédige `CLAUDE.md` (§4) + `guardrails.py` (§10) + journal d’audit. Teste les garde-fous avec des cas VERT/AMBRE/ROUGE et une tentative d’accès à une entité exclue (le compteur doit s’incrémenter et l’action être bloquée).

**Phase 3** — Crée le roster d’agents (§5) + l’Agent Factory (§6). Vérifie que la Factory crée un agent valide depuis un besoin d’une ligne.

**Phase 4** — Construis `orchestrator.py` (§7) + les slash commands (§13).

**Phase 5 — Run à blanc 🚦** : exécute **UN cycle complet en `--dry-run`** (zéro effet de bord externe). Montre-moi le brief CEO et la file d’approbation. Attends ma validation.

**Phase 6** — Remise : `README.md` (lancer en continu, approuver, étendre, passer du dry-run au réel).

-----

## 15. DEFINITION OF DONE (critères d’acceptation testables)

- [ ] `/run-cycle` exécute une boucle de bout en bout en `--dry-run` **sans aucun effet de bord externe**.
- [ ] Chaque action est journalisée ; **toute action ROUGE est mise en file, jamais exécutée**.
- [ ] L’Agent Factory crée un nouvel agent valide depuis un besoin en une phrase.
- [ ] L’exclusion de données est appliquée **aux deux couches** ; `attempted_access_count` = 0 et l’enforcement est prouvé par un test.
- [ ] Un humain peut **pause / inspecter / approuver / rejeter / resume**.
- [ ] Le brief CEO est généré, lisible, et expose la file d’arbitrage.
- [ ] Les plafonds budgétaires déclenchent un hard stop quand dépassés.

-----

**Commence par la Phase 0. Ne code rien avant ma validation du cadrage.**