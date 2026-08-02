# Jarvis v6

Écosystème d'IA auto-constructible, piloté depuis Telegram, voix humaine assumée.

**Statut**: Phase 1 — Jalon 1.1 (socle).

## Principes directeurs (ordre d'arbitrage)

1. Sécurité > autonomie > vitesse.
2. Humain dans le ton, honnête sur la nature. Jamais prétendre être humain.
3. Conversation > commande.
4. Intentions en entrée, infrastructure en sortie.
5. Preuve avant échelle — France 95% avant expansion.
6. Une zone = un mini-produit.
7. Mesurer > croire.
8. Respect du prospect — zéro manipulation, opt-out sacré.
9. Isolation multi-tenant stricte.
10. Périmètre > service — refus plutôt que traitement partiel.
11. Transparence totale envers Laurent.
12. Mon temps > ton élégance.

## Périmètre

**Inclus** : Jonction, Deco & Pro, Pattom, perso, finances, immo, recherche, dev, veille, voyages.
**Exclusion absolue** : Sika, Parexlanko. Double verrou (routeur + system prompt), compteur `scope_violations` = 0.

## Layout

```
jarvis/
  core/          # config, scope filter, model router, budget manager
  agents/        # base agent, Jarvis orchestrateur, Builder, specialists
  voice/         # DNA, banned phrases, zone modulation, lint
  memory/        # 4-layer memory interface
  bus/           # message bus avec trace_id
  queue/         # persistent queue
  models/        # router Haiku/Sonnet/Opus + Ollama fallback
  security/      # prompt injection defense, secrets, kill switch
  rgpd/          # forget, export, art.30 register, DPA
  telegram_bot/  # bot handlers + reporting format
  dashboard/     # FastAPI observability
  evals/         # golden tasks + harness
  observability/ # audit trail, metrics
  compliance/    # registres legaux par zone
  playbooks/     # playbooks par venture/zone
  tenancy/       # isolation multi-tenant
tests/
goldens/         # golden tasks YAML
config/          # YAML configs (allowlists, providers, zones)
migrations/      # SQL Supabase
docs/
```

## Démarrage

```bash
cp .env.example .env
# Éditer .env avec tes credentials
docker compose up -d
```

## Format rapport Telegram (imposé)

Chaque jalon livré envoie ce format :

```
🟢 validé    : [ce qui passe les evals]
📦 livré     : [artefacts]
🧪 tests+evals : [N/M]
💶 coût réel : [€] vs estimé [€]
📈 métrique  : [KPI si pertinent]
⏭️ prochain  : [jalon suivant]
❓ besoin de toi : [credentials / décision / rien]
```

## Garde-fous v1

- Filtre scope Sika/Parexlanko double-verrouillé (voir `core/scope.py`)
- Voice lint sur chaque message sortant (voir `voice/lint.py`)
- Whitelist Telegram stricte (voir `telegram_bot/auth.py`)
- Kill switch global (voir `security/kill_switch.py`)
- Hard stop budget (voir `core/budget.py`)
- Niveau 1 max sur tous agents tant qu'évals < seuil
