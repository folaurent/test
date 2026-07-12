"""
factory.py — l'Agent Factory (méta-agent, §6).

Quand le Chief of Staff détecte un manque de compétence, il invoque la Factory
avec un besoin en langage naturel. La Factory :
  1. Traduit le besoin en spec d'agent (gabarit §5).
  2. Vérifie qu'aucun agent existant ne couvre déjà ce besoin (anti-prolifération).
  3. Écrit un fichier .claude/agents/<slug>.md valide.
  4. Enregistre l'agent dans la table `agents` (created_by = agent-factory).
  5. Le rend immédiatement disponible au routage.

Garde-fou : un nouvel agent n'hérite QUE des classes VERT/AMBRE.
Toute capacité ROUGE est désactivée par défaut (approbation humaine requise).
"""

from __future__ import annotations

import os
import re

import memory

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS_DIR = os.path.join(ROOT, ".claude", "agents")

# Mots vides FR/EN pour extraire des mots-clés du besoin.
_STOP = set("""
un une des le la les de du d au aux et ou pour qui que quoi avec sur dans en a à the a an of to for and or with on in que par plus afin
besoin agent capable gérer gerer faire creer créer nouveau nouvelle équipe equipe nous notre
""".split())


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    words = [w for w in text.split() if w and w not in _STOP]
    slug = "-".join(words[:3]) or "agent"
    return slug[:40].strip("-")


def _keywords(text: str) -> set:
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    return {w for w in text.split() if w not in _STOP and len(w) > 3}


def find_overlap(conn, need: str, threshold: float = 0.5):
    """Détecte un agent existant couvrant déjà le besoin (anti-prolifération)."""
    need_kw = _keywords(need)
    if not need_kw:
        return None
    best, best_score = None, 0.0
    for a in memory.list_agents(conn, status=None):
        existing_kw = _keywords(f"{a['role']} {a['mission']}")
        if not existing_kw:
            continue
        overlap = len(need_kw & existing_kw) / len(need_kw)
        if overlap > best_score:
            best, best_score = a, overlap
    if best and best_score >= threshold:
        return {"agent": best["name"], "overlap": round(best_score, 2)}
    return None


def _spec_markdown(slug, role, mission, need) -> str:
    return f"""---
name: {slug}
role: {role}
mission: {mission}
triggers: Le Chief of Staff invoque cet agent quand une initiative requiert : {need}
inputs: Brief de la tâche, contexte de l'initiative, contraintes du cycle.
tools: [read, write_local, analyze]   # liste blanche — capacités VERT/AMBRE uniquement
deliverables: Livrable écrit dans /artifacts/<initiative>/, référencé dans tasks.output_ref.
success_criteria: Livrable conforme au brief, sources citées ou hypothèses marquées.
escalation_rules: Remonte au CEO toute décision ROUGE (coût, légal, externe, irréversible).
max_budget: 0   # dry-run pur ; toute dépense réelle nécessite approbation
action_class: GREEN   # par défaut ; AMBRE possible sous plafond ; ROUGE désactivé
---

# {role}

> Agent créé dynamiquement par l'**Agent Factory** pour répondre au besoin :
> « {need} »

## Persona
Tu es un spécialiste pragmatique et factuel. Tu produis un travail vérifiable.

## Méthode de travail
1. Clarifie l'objectif et les critères de succès de la tâche.
2. Produis le livrable demandé, structuré et concis.
3. Cite tes sources ; marque explicitement toute hypothèse ou incertitude.
4. Dépose le livrable dans `/artifacts/` et signale à quel KPI il contribue.

## Format de sortie
Markdown structuré (titre, contexte, livrable, prochaines étapes, sources/hypothèses).

## Contraintes & garde-fous (rappel)
- **Capacités VERT/AMBRE uniquement.** Toute action ROUGE (argent, légal, envoi
  vers de vraies personnes, publication, suppression) est **interdite** sans
  approbation humaine : tu la décris et tu la remontes, tu ne l'exécutes jamais.
- **Exclusion de données stricte** : ne jamais ingérer, traiter ou référencer
  *Sika*, *Parexlanko* ou toute entité de `data_exclusions`.
- **Pas de fabrication** : une incertitude se déclare, elle ne s'invente pas.
- Reste dans ton `max_budget` ; tout est journalisé dans l'`audit_log`.
"""


def create_agent(conn, need: str, role: str | None = None,
                 mission: str | None = None, actor="agent-factory") -> dict:
    """Crée (ou réutilise) un agent à partir d'un besoin en une phrase."""
    overlap = find_overlap(conn, need)
    if overlap:
        memory.audit(conn, actor, "FACTORY_SKIPPED_DUPLICATE",
                     {"need": need, **overlap}, action_class="GREEN")
        return {"status": "reused", **overlap}

    slug = slugify(need)
    # Évite la collision de slug.
    base, n = slug, 2
    while memory.get_agent(conn, slug):
        slug = f"{base}-{n}"
        n += 1

    role = role or f"Spécialiste : {need.strip().capitalize()}"
    mission = mission or f"Traiter les tâches liées à : {need.strip()}"

    os.makedirs(AGENTS_DIR, exist_ok=True)
    path = os.path.join(AGENTS_DIR, f"{slug}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(_spec_markdown(slug, role, mission, need))

    rel_path = os.path.relpath(path, ROOT)
    memory.upsert_agent(conn, slug, role, mission, rel_path,
                        tools="read,write_local,analyze", created_by=actor)
    memory.audit(conn, actor, "FACTORY_CREATED_AGENT",
                 {"slug": slug, "need": need, "path": rel_path,
                  "inherited_classes": ["GREEN", "AMBER"], "red_disabled": True},
                 action_class="GREEN")
    return {"status": "created", "slug": slug, "path": rel_path}
