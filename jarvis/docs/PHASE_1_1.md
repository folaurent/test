# Phase 1 — Jalon 1.1 (socle)

## Livré

- **Scaffolding** : `pyproject.toml`, `Dockerfile`, `docker-compose.yml` (app + Redis + Ollama en fallback), `.env.example` avec tous les champs (Telegram, Supabase, Anthropic/OpenAI/Ollama, budgets, dashboard, security, S3, DPA/ZDR flag).
- **Config** (`jarvis/core/config.py`) : pydantic-settings avec validator qui re-force Sika/Parexlanko en exclusion même si env var essaie de les retirer.
- **Scope filter double verrou** (`jarvis/core/scope.py`) :
  - Verrou 1 : filtre tag + regex (`\bsika\b`, `\bparex[\s\-]?lanko\b`) sur bus + entrées.
  - Verrou 2 : `SCOPE_SYSTEM_PREFIX` injecté dans chaque `AgentBase.system_prompt()`.
  - `ScopeFilter.validate_boot()` refuse le démarrage si la config ment.
- **Voice guide** (`jarvis/voice/`) :
  - `dna.py` : 5 traits, `DISCLOSURE_POLICY`, phrases bannies FR avec remplacement, patterns de manipulation, emojis d'ouverture interdits.
  - `zones.py` : 13 profils zonaux (FR, DACH, UK, US, CA, IT, ES, PT, BENELUX, NORDICS, JP, KR, CN) avec formalité + heures d'envoi.
  - `lint.py` : `VoiceLint` avec règles hard/soft, score, détection déni d'IA, manipulation, prénom répété, URL shorteners, rafales de ! ou MAJ, >1 question, emojis excessifs.
  - `voice_system_prompt()` injecté auto pour les agents `human_facing=True`.
- **Model router** (`jarvis/core/model_router.py`) : table intention → tier (Haiku 4.5 / Sonnet 4.6 / Opus 4.7 / Ollama fallback).
- **Budget manager** (`jarvis/core/budget.py`) : hard stop par défaut sur €/mois LLM, €/mois infra, tokens/mois, questions Telegram/jour.
- **Message bus** (`jarvis/bus/`) : schéma strict avec `trace_id`, scope check sur chaque send (tag + payload), backend async in-memory (interface Supabase prête).
- **Queue persistante** (`jarvis/queue/`) : idempotency key, retry exponentiel 2→4→8→16s, backend mémoire (Redis en prod).
- **Mémoire 4 couches** (`jarvis/memory/memory.py`) : L1 working / L2 episodic / L3 semantic / L4 archive, tags obligatoires (`venture`, `zone`, `pii_level`, `source_trust`, `retention_days`, `subject_id`), GC expiration, RGPD `forget_subject()` + `export_subject()`.
- **Sécurité** (`jarvis/security/`) :
  - `kill_switch.py` : flag fichier, `assert_ok()` au boot.
  - `injection.py` : encapsulation entrées externes, scan jailbreaks, canary leak detection.
  - `secrets.py` : SecretStore Fernet.
- **RGPD** (`jarvis/rgpd/`) :
  - `register.py` : registre article 30 avec refus si DPA Anthropic non signé.
  - `rights.py` : droits erasure et portabilité.
- **Agents** (`jarvis/agents/`) :
  - `base.py` : `AgentBase` + `AgentCharter` + `AutonomyLevel` (0 shadow → 3 full). System prompt assemblé (scope + voice + rôle + autonomie + allowlist tools).
  - `builder.py` : Builder v0 — `parse_intent()` (venture + zone + kind), `draft_plan()` (spécialistes, goldens, coût, compliance, risques), `as_telegram_card()` pour validation.
  - `jarvis_orchestrator.py` : orchestrateur stub (pipeline complet en Jalon 1.2).
- **Telegram** (`jarvis/telegram_bot/`) :
  - `auth.py` : whitelist stricte users + chats.
  - `bot.py` : dispatcher aiogram, commandes `/status /ping /scope`.
  - `report.py` : `MilestoneReport` + `format_report()` (format 🟢📦🧪💶📈⏭️❓ imposé).
- **Dashboard** (`jarvis/dashboard/app.py`) : FastAPI avec endpoints stubbés pour toutes les sections (live, agents, violations, budget, zones, voice_health, compliance, builds, conversations) + auth Bearer.
- **Evals** (`jarvis/evals/`) : harness YAML + golden `voice_fr.yml` (5 goldens : phrases bannies, divulgation, 1 question, refus Sika, refus Parexlanko).
- **Observability** : logger structlog JSON + audit trail JSONL.
- **Configs** : `config/providers_allowlist.yml`, `config/critical_configs.yml`.

## Tests : 58/58 ✅

```
tests/test_agent_base.py        5 passed
tests/test_budget.py            5 passed
tests/test_builder.py           7 passed
tests/test_bus.py               4 passed
tests/test_eval_harness.py      3 passed
tests/test_injection.py         4 passed
tests/test_memory.py            5 passed
tests/test_model_router.py      5 passed
tests/test_queue.py             3 passed
tests/test_report.py            1 passed
tests/test_scope.py             8 passed
tests/test_voice_lint.py        8 passed
```

## À faire avant Jalon 1.2

**Bloquant — à fournir par Laurent** :

1. `TELEGRAM_BOT_TOKEN` + liste des user IDs whitelist.
2. `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` (projet région EU).
3. `ANTHROPIC_API_KEY` + statut DPA Zero Data Retention (flag `ANTHROPIC_ZDR`).
4. Confirmation budget infra initial (suggéré : 100 €/mois).
5. VPS cible pour déploiement (ou OK pour OVH Performance 1 à ~25€/mois).
6. Providers email à approuver : Resend (UE) et/ou Postmark (US) ?

**Indépendant — Jalon 1.2** :

- Brancher Supabase pour bus, queue, mémoire L2/L3.
- Démarrer bot Telegram polling et dashboard FastAPI côte à côte.
- Implémenter Jarvis orchestrateur pipeline complet (Router → Planner → Dispatcher → Aggregator → Verifier).
- Builder v0 → v1 : génération de plan validée par Opus 4.7, exécution git signée.
- Premier spécialiste créé par Builder : **Dev** (pour auto-test du pipeline).
- 5 goldens globales Jarvis.
