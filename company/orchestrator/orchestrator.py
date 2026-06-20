#!/usr/bin/env python3
"""
orchestrator.py — exécute UN cycle de gestion complet (§7).

Étapes (dans l'ordre, chacune journalisée) :
  0. CHECK     — si STATE == PAUSED -> arrêt immédiat.
  1. INTAKE    — idées du CEO + signaux + items en attente (filtre exclusions).
  2. TRIAGE    — Chief of Staff score (impact × effort × risque) et route.
  3. PLAN      — CEO sélectionne les initiatives, fixe objectifs + KPI, alloue budget.
  4. DISPATCH  — assigne aux agents ; compétence manquante -> Agent Factory.
  5. EXECUTE   — agents produisent leurs livrables ; toute action passe par guardrails.
  6. REVIEW    — quality-retro + CEO contrôlent les livrables.
  7. MEASURE   — mise à jour des metrics vs cibles.
  8. ADAPT     — rétrospective -> leçons + re-score des agents.
  9. REPORT    — brief CEO + file d'approbation pour l'humain.

Le cycle est idempotent et reprenable : tout l'état vit dans company.db et /artifacts.
--dry-run (par défaut) : aucun effet de bord externe.
"""

from __future__ import annotations

import argparse
import os
import re

import factory
import guardrails as G
import llm
import memory
import reporting
from connectors import shopify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS_DIR = os.path.join(ROOT, ".claude", "agents")
ARTIFACTS_DIR = os.path.join(ROOT, "artifacts")

# Plafonds (cadrage : dry-run pur, plafonds symboliques en garde-fou)
CYCLE_CAP = 10.0
GLOBAL_CAP = 100.0

# Banque d'idées du CEO (domaine : e-commerce / contenu).
CEO_IDEA_BANK = [
    ("Optimiser les fiches produit pour la conversion",
     "Des fiches plus claires augmentent le taux de conversion",
     "growth-marketing", "conversion_rate", "skill:copywriting SEO produit"),
    ("Calendrier éditorial de contenu SEO",
     "Un contenu régulier augmente le trafic organique",
     "growth-marketing", "organic_traffic", None),
    ("Réduire le taux d'abandon de panier",
     "Simplifier le checkout réduit l'abandon",
     "product-rnd", "cart_abandon_rate", None),
    ("Programme de fidélité / rétention",
     "Un programme de fidélité augmente la valeur client",
     "operations", "repeat_purchase_rate", "skill:CRM lifecycle email"),
]

# KPI cibles de l'entreprise (e-commerce / contenu).
KPI_TARGETS = {
    "conversion_rate": (2.5, "%"),
    "organic_traffic": (10000, "visits"),
    "cart_abandon_rate": (60, "%"),
    "repeat_purchase_rate": (25, "%"),
}


# ----------------------------------------------------------------------
#  Bootstrap : synchronise les agents .md -> table agents
# ----------------------------------------------------------------------
def _parse_frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---", text, flags=re.DOTALL)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                fm[k.strip()] = v.strip()
    return fm


def sync_agents(conn):
    if not os.path.isdir(AGENTS_DIR):
        return 0
    count = 0
    for fn in sorted(os.listdir(AGENTS_DIR)):
        if not fn.endswith(".md"):
            continue
        path = os.path.join(AGENTS_DIR, fn)
        with open(path, "r", encoding="utf-8") as f:
            fm = _parse_frontmatter(f.read())
        name = fm.get("name") or fn[:-3]
        memory.upsert_agent(conn, name, fm.get("role", ""), fm.get("mission", ""),
                            os.path.relpath(path, ROOT), fm.get("tools", ""),
                            created_by="bootstrap")
        count += 1
    return count


# ----------------------------------------------------------------------
#  Cognition LLM (action AMBRE — réelle en --live, simulée en dry-run)
# ----------------------------------------------------------------------
def _charge_llm(conn, cycle_id, res, actor):
    """Impute le coût d'un appel LLM réel au budget cycle + global, journalisé."""
    if not res:
        return
    cost = res.get("cost", 0.0)
    cycle_period = f"cycle:{cycle_id}"
    if not G.check_budget(conn, cycle_period, cost, CYCLE_CAP) or \
       not G.check_budget(conn, "global", cost, GLOBAL_CAP):
        return
    memory.add_spend(conn, cycle_period, cost, CYCLE_CAP)
    memory.add_spend(conn, "global", cost, GLOBAL_CAP)
    memory.audit(conn, actor, "LLM_CALL",
                 {"model": res.get("model"), "in": res.get("in_tokens"),
                  "out": res.get("out_tokens"), "cost": cost}, action_class="AMBER")


def _ceo_ideate_llm(conn, cycle_id, signals, dry_run, actor="ceo"):
    """Le CEO génère des hypothèses via LLM (live) ou renvoie None (stub)."""
    sys = ("Tu es l'Agent CEO d'une entreprise e-commerce/contenu. "
           "Génère 2 hypothèses de croissance actionnables. "
           "Réponds en JSON: une liste d'objets {\"title\":..., \"hypothesis\":...}. "
           "Cite des leviers réels (conversion, SEO, rétention). N'invente aucune donnée. "
           "N'utilise JAMAIS les entités Sika ou Parexlanko.")
    usr = "Signaux de l'entreprise:\n" + "\n".join(f"- {s}" for s in signals.get("signals", []))
    res = llm.complete(sys, usr, dry_run=dry_run, max_tokens=600)
    _charge_llm(conn, cycle_id, res, actor)
    if not res:
        return None
    import json as _json
    try:
        text = res["text"].strip()
        start, end = text.find("["), text.rfind("]")
        ideas = _json.loads(text[start:end + 1]) if start >= 0 else []
        out = []
        for it in ideas[:2]:
            if isinstance(it, dict) and it.get("title"):
                out.append({"title": str(it["title"])[:120],
                            "hypothesis": str(it.get("hypothesis", ""))[:300],
                            "owner": "growth-marketing", "kpi": None, "skill": None})
        return out or None
    except Exception:
        return None


# ----------------------------------------------------------------------
#  Phases du cycle
# ----------------------------------------------------------------------
def _derive_initiatives_from_signals(signals):
    """
    Idéation déterministe PILOTÉE PAR LE DIAGNOSTIC réel (depuis les signaux).
    Règles transparentes sur le bloc `context` ; renvoie des initiatives reliées
    aux vrais problèmes de la boutique. Repli si pas de contexte exploitable.
    """
    ctx = signals.get("context") or {}
    funnel = ctx.get("funnel_30d") or {}
    sources = ctx.get("traffic_sources") or {}
    catalog = ctx.get("catalog") or {}
    ideas = []

    sessions = funnel.get("sessions", 0)
    carts = funnel.get("cart_additions", 0)
    completed = funnel.get("completed", 0)

    # 1) Conversion nulle malgré des paniers -> réparer le tunnel paiement.
    if carts and completed == 0:
        ideas.append({
            "title": "Réparer le tunnel panier → paiement",
            "hypothesis": f"{carts} paniers et 0 achat sur 30j : un blocage au checkout "
                          "(frais, moyens de paiement, bug) tue la conversion.",
            "owner": "product-rnd", "kpi": "cart_abandon_rate", "skill": None})

    # 2) Trafic faible et quasi exclusivement direct -> lancer l'acquisition SEO.
    total_src = sum(sources.values()) or 0
    direct = sources.get("direct", 0)
    if total_src and (direct / total_src) > 0.8:
        ideas.append({
            "title": "Lancer l'acquisition SEO (contenu produit + guides pose)",
            "hypothesis": "Le trafic est ~exclusivement direct : aucun canal d'acquisition "
                          "n'apporte de nouveaux visiteurs. Du contenu SEO ciblé "
                          "(travertin, carrelage, pose) ouvrirait l'organique.",
            "owner": "growth-marketing", "kpi": "organic_traffic", "skill": None})
        ideas.append({
            "title": "Activer un canal social (visuels produits / inspiration déco)",
            "hypothesis": "Un catalogue déco visuel se prête au social ; 1 seule session "
                          "social sur 30j = canal inexploité.",
            "owner": "growth-marketing", "kpi": "organic_traffic",
            "skill": "social ads & contenu visuel déco"})

    # 3) Catalogue avec produits archivés -> auditer l'indexabilité.
    if catalog.get("more_pages") or catalog.get("active_products_min"):
        ideas.append({
            "title": "Auditer l'indexabilité du catalogue (produits archivés/SEO)",
            "hypothesis": "Catalogue large mais produits archivés/non indexés = perte de "
                          "surface organique et de pages d'entrée.",
            "owner": "operations", "kpi": "organic_traffic", "skill": None})

    return ideas


def phase_intake(conn, cycle_id, dry_run, actor="ceo"):
    """Rassemble idées CEO + items en attente, filtre les exclusions (verrou 1)."""
    proposed = memory.list_initiatives(conn, status="proposed")
    signals = shopify.fetch_signals(dry_run=dry_run)
    raw_ideas = []
    # Si peu d'items en file, le CEO génère des hypothèses (LLM si live, sinon banque).
    if len(proposed) < 2:
        llm_ideas = _ceo_ideate_llm(conn, cycle_id, signals, dry_run, actor)
        if llm_ideas:
            raw_ideas.extend(llm_ideas)
        else:
            # Idéation déterministe pilotée par le diagnostic réel.
            derived = _derive_initiatives_from_signals(signals)
            if derived:
                raw_ideas.extend(derived)
            else:
                for title, hyp, owner, kpi, skill in CEO_IDEA_BANK:
                    raw_ideas.append({"title": title, "hypothesis": hyp, "owner": owner,
                                      "kpi": kpi, "skill": skill})

    # VERROU 1 — filtre d'exclusion de données à l'INTAKE.
    texts = [f"{i['title']} {i['hypothesis']}" for i in raw_ideas]
    clean_texts, blocked = G.filter_excluded(conn, texts, actor="chief-of-staff")
    clean = [raw_ideas[i] for i, t in enumerate(texts) if t in clean_texts]

    for idea in clean:
        memory.add_initiative(conn, idea["title"], idea["hypothesis"],
                              rationale="Hypothèse générée par le CEO à l'INTAKE.",
                              owner=idea["owner"], expected_kpi=idea["kpi"])
    memory.audit(conn, actor, "INTAKE",
                 {"new_ideas": len(clean), "blocked": len(blocked),
                  "data_source": signals.get("source")})
    return {"new": len(clean), "blocked": blocked, "source": signals.get("source")}


def _triage_llm(conn, cycle_id, proposed, signals, dry_run, actor="chief-of-staff"):
    """Scoring raisonné par LLM : renvoie {id: {priority, rationale}} ou None."""
    if not proposed:
        return None
    sys = ("Tu es le Chief of Staff. Score chaque initiative par impact × (1/effort) × "
           "(1/risque) pour une boutique e-commerce. Réponds en JSON: liste d'objets "
           "{\"id\":<int>, \"priority\":<float 0-3>, \"rationale\":\"...\"}. "
           "Appuie-toi sur les signaux réels. N'invente aucune donnée.")
    items = "\n".join(f"#{i['id']} {i['title']} — {i['hypothesis']}" for i in proposed)
    usr = ("Signaux:\n" + "\n".join(f"- {s}" for s in signals.get("signals", [])) +
           "\n\nInitiatives:\n" + items)
    res = llm.complete(sys, usr, dry_run=dry_run, max_tokens=800)
    _charge_llm(conn, cycle_id, res, actor)
    if not res:
        return None
    import json as _json
    try:
        text = res["text"]
        start, end = text.find("["), text.rfind("]")
        rows = _json.loads(text[start:end + 1]) if start >= 0 else []
        out = {}
        for r in rows:
            if isinstance(r, dict) and "id" in r:
                out[int(r["id"])] = {"priority": round(float(r.get("priority", 0)), 3),
                                     "rationale": str(r.get("rationale", ""))[:300]}
        return out or None
    except Exception:
        return None


def phase_triage(conn, cycle_id, dry_run, actor="chief-of-staff"):
    """Score chaque initiative proposée. LLM raisonné si live, sinon heuristique."""
    proposed = memory.list_initiatives(conn, status="proposed")
    signals = shopify.fetch_signals(dry_run=dry_run)
    llm_scores = _triage_llm(conn, cycle_id, proposed, signals, dry_run, actor)
    for i, init in enumerate(proposed):
        if llm_scores and init["id"] in llm_scores:
            sc = llm_scores[init["id"]]
            memory.set_initiative(conn, init["id"], priority=sc["priority"], status="planned",
                                  rationale=sc["rationale"] or init.get("rationale"))
        else:
            # Heuristique déterministe et transparente (repli sans LLM).
            impact = 0.9 - 0.1 * (i % 4)
            effort = 0.4 + 0.1 * (i % 3)
            risk = 0.3 + 0.1 * (i % 2)
            priority = round(impact / (effort * (1 + risk)), 3)
            memory.set_initiative(conn, init["id"], priority=priority, status="planned")
    memory.audit(conn, actor, "TRIAGE",
                 {"scored": len(proposed), "reasoned": bool(llm_scores)})
    return {"scored": len(proposed), "reasoned": bool(llm_scores)}


def phase_plan(conn, cycle_id, actor="ceo", max_initiatives=2):
    """Le CEO sélectionne les initiatives du cycle, fixe budget cycle, lance."""
    planned = memory.list_initiatives(conn, status="planned")
    selected = planned[:max_initiatives]
    for init in selected:
        memory.set_initiative(conn, init["id"], status="running")
    memory.set_budget(conn, f"cycle:{cycle_id}", 0.0, CYCLE_CAP)
    if not memory.get_budget(conn, "global"):
        memory.set_budget(conn, "global", 0.0, GLOBAL_CAP)
    memory.audit(conn, actor, "PLAN",
                 {"selected": [i["id"] for i in selected], "cycle_cap": CYCLE_CAP})
    return selected


def phase_dispatch(conn, selected, actor="chief-of-staff"):
    """Assigne aux agents ; si compétence manquante -> Agent Factory."""
    new_agents = []
    for init in selected:
        owner = init["owner_agent"]
        # Détecte un besoin de compétence encodé dans le rationale/kpi.
        skill_needed = None
        for title, hyp, o, kpi, skill in CEO_IDEA_BANK:
            if title == init["title"] and skill:
                skill_needed = skill.replace("skill:", "")
        if skill_needed and not memory.get_agent(conn, owner):
            owner = "growth-marketing"
        if skill_needed:
            res = factory.create_agent(conn, skill_needed)
            if res["status"] == "created":
                new_agents.append(res["slug"])
                owner = res["slug"]
        if not memory.get_agent(conn, owner):
            owner = "chief-of-staff"
        memory.set_initiative(conn, init["id"], owner_agent=owner)
        memory.add_task(conn, init["id"], owner,
                        f"Produire le livrable pour : {init['title']}")
    memory.audit(conn, actor, "DISPATCH", {"new_agents": new_agents})
    return new_agents


def phase_execute(conn, cycle_id, dry_run, actor="ceo"):
    """Les agents produisent leurs livrables. Toute action passe par le gate guardrails."""
    todo = memory.list_tasks(conn, status="todo")
    cycle_period = f"cycle:{cycle_id}"
    for t in todo:
        init = memory.fetchone(conn, "SELECT * FROM initiatives WHERE id=?", (t["initiative_id"],))
        agent = t["assigned_agent"]

        # 1) Production du livrable = action VERT (fichier local).
        init_dir = os.path.join(ARTIFACTS_DIR, f"initiative_{t['initiative_id']}")
        os.makedirs(init_dir, exist_ok=True)
        artifact = os.path.join(init_dir, f"task_{t['id']}_{agent}.md")
        content = (
            f"# Livrable — {init['title']}\n\n"
            f"- **Agent** : {agent}\n- **Initiative** : #{t['initiative_id']}\n"
            f"- **Hypothèse** : {init['hypothesis']}\n- **KPI visé** : {init['expected_kpi']}\n\n"
            f"## Travail (simulé en dry-run)\n"
            f"Analyse et recommandations pour « {init['title']} ».\n\n"
            f"## Sources / hypothèses\n"
            f"- Hypothèse de travail (à valider avec données réelles).\n"
        )
        # Passe par le gate : production locale (VERT).
        verdict = G.gate_action(conn, agent, f"write_local artifact: {init['title']}",
                                payload={"path": os.path.relpath(artifact, ROOT)},
                                explicit_class="GREEN", cost=0.0,
                                cycle_period=cycle_period, cycle_cap=CYCLE_CAP,
                                global_cap=GLOBAL_CAP, dry_run=dry_run)
        if verdict["outcome"] == "executed":
            with open(artifact, "w", encoding="utf-8") as f:
                f.write(content)
            memory.complete_task(conn, t["id"], os.path.relpath(artifact, ROOT))

        # 2) Chaque initiative génère une action externe candidate (démonstration
        #    de la taxonomie). Ici : publier le contenu = ROUGE -> mise en file.
        G.gate_action(conn, agent,
                      f"publish content for initiative: {init['title']}",
                      payload={"channel": "site"}, explicit_class=None, cost=0.0,
                      cycle_period=cycle_period, cycle_cap=CYCLE_CAP,
                      global_cap=GLOBAL_CAP, dry_run=dry_run)
    memory.audit(conn, actor, "EXECUTE", {"tasks": len(todo)})
    return {"tasks": len(todo)}


def phase_review(conn, actor="quality-retro"):
    """Contrôle des livrables : présence + conformité minimale."""
    done = memory.list_tasks(conn, status="done")
    ok = 0
    for t in done:
        if t["output_ref"] and os.path.exists(os.path.join(ROOT, t["output_ref"])):
            ok += 1
    memory.audit(conn, actor, "REVIEW", {"checked": len(done), "ok": ok})
    return {"checked": len(done), "ok": ok}


def phase_measure(conn, dry_run, actor="data-analytics"):
    """Met à jour les metrics vs cibles depuis Shopify (réel) ou simulé."""
    period = f"cycle:{memory.cycle_count(conn)}"
    signals = shopify.fetch_signals(dry_run=dry_run)
    measured = {k["name"]: k for k in signals.get("kpis", [])}
    for name, (target, unit) in KPI_TARGETS.items():
        kpi = measured.get(name)
        # Valeur réelle disponible (mesurée, non-hypothèse) -> on l'utilise.
        # NB : 0 est une valeur mesurée valide (ex. conversion 0%), pas une absence.
        if kpi and not kpi.get("assumption") and kpi.get("value") is not None:
            value = round(float(kpi["value"]), 2)
        else:
            # Sinon : amélioration simulée vs cycle précédent (transparent).
            prev = memory.fetchone(
                conn,
                "SELECT value FROM metrics WHERE name=? ORDER BY recorded_at DESC LIMIT 1",
                (name,))
            base = prev["value"] if prev else target * 0.6
            value = round(base * 1.05, 2)
        memory.record_metric(conn, name, value, unit, target, period)
    memory.audit(conn, actor, "MEASURE",
                 {"kpis": list(KPI_TARGETS), "data_source": signals.get("source")})
    return {"kpis": len(KPI_TARGETS), "source": signals.get("source")}


def _retro_llm(conn, cycle_id, selected, signals, dry_run, actor="quality-retro"):
    """Rétrospective raisonnée par LLM : renvoie {id: {learning, action_taken}} ou None."""
    if not selected:
        return None
    sys = ("Tu es l'agent quality-retro. Pour chaque initiative close, tire UNE leçon "
           "factuelle et réutilisable. Réponds en JSON: liste d'objets "
           "{\"id\":<int>, \"learning\":\"...\", \"action_taken\":\"...\"}. "
           "Faits seulement, pas d'opinion ni de fabrication.")
    items = "\n".join(f"#{i['id']} {i['title']}" for i in selected)
    usr = ("Signaux:\n" + "\n".join(f"- {s}" for s in signals.get("signals", [])) +
           "\n\nInitiatives closes ce cycle:\n" + items)
    res = llm.complete(sys, usr, dry_run=dry_run, max_tokens=700)
    _charge_llm(conn, cycle_id, res, actor)
    if not res:
        return None
    import json as _json
    try:
        text = res["text"]
        start, end = text.find("["), text.rfind("]")
        rows = _json.loads(text[start:end + 1]) if start >= 0 else []
        return {int(r["id"]): {"learning": str(r.get("learning", ""))[:300],
                               "action_taken": str(r.get("action_taken", ""))[:300]}
                for r in rows if isinstance(r, dict) and "id" in r} or None
    except Exception:
        return None


def phase_adapt(conn, selected, cycle_id, dry_run, actor="quality-retro"):
    """Rétrospective : leçons (LLM raisonné ou canned) + re-score des agents."""
    signals = shopify.fetch_signals(dry_run=dry_run)
    llm_lessons = _retro_llm(conn, cycle_id, selected, signals, dry_run, actor)
    for init in selected:
        memory.set_initiative(conn, init["id"], status="closed",
                              result="Cycle clos — livrable produit, publication en attente d'approbation.")
        if llm_lessons and init["id"] in llm_lessons:
            les = llm_lessons[init["id"]]
            memory.add_lesson(conn, init["id"],
                              observation=f"Initiative « {init['title']} » (rétro raisonnée).",
                              learning=les["learning"] or "—",
                              action_taken=les["action_taken"] or "—")
        else:
            memory.add_lesson(conn, init["id"],
                              observation=f"Initiative « {init['title']} » exécutée en dry-run.",
                              learning="Les actions de publication sont bien interceptées en ROUGE.",
                              action_taken="Mise en file d'approbation, aucune publication automatique.")
    # Re-score simple : agents avec tâches terminées montent légèrement.
    for a in memory.list_agents(conn):
        done = memory.fetchone(conn,
                               "SELECT COUNT(*) c FROM tasks WHERE assigned_agent=? AND status='done'",
                               (a["name"],))
        score = min(1.0, 0.5 + 0.05 * (done["c"] if done else 0))
        memory.set_agent_score(conn, a["name"], round(score, 3))
    memory.audit(conn, actor, "ADAPT",
                 {"closed": len(selected), "reasoned": bool(llm_lessons)})
    return {"closed": len(selected), "reasoned": bool(llm_lessons)}


# ----------------------------------------------------------------------
#  Exécution d'un cycle complet
# ----------------------------------------------------------------------
def run_cycle(dry_run=True):
    conn = memory.connect()

    # 0. CHECK — kill switch
    if G.is_paused():
        memory.audit(conn, "orchestrator", "CYCLE_ABORTED_PAUSED", action_class="GREEN")
        print("⏸️  STATE == PAUSED — cycle non exécuté (kill switch actif).")
        return

    mode = "dry-run" if dry_run else "live"
    cycle_id = memory.start_cycle(conn, mode)
    sync_agents(conn)
    memory.audit(conn, "orchestrator", "CYCLE_START", {"cycle_id": cycle_id, "mode": mode})

    intake = phase_intake(conn, cycle_id, dry_run)
    phase_triage(conn, cycle_id, dry_run)
    selected = phase_plan(conn, cycle_id)
    new_agents = phase_dispatch(conn, selected)
    phase_execute(conn, cycle_id, dry_run)
    phase_review(conn)
    phase_measure(conn, dry_run)
    phase_adapt(conn, selected, cycle_id, dry_run)

    path = reporting.write_brief(conn, cycle_id, mode, new_agents,
                                 budget_caps=(CYCLE_CAP, GLOBAL_CAP), dry_run=dry_run)
    memory.end_cycle(conn, cycle_id,
                     f"intake={intake['new']} selected={len(selected)} new_agents={len(new_agents)}")
    memory.audit(conn, "orchestrator", "CYCLE_END", {"cycle_id": cycle_id, "report": path})

    print(f"✅ Cycle #{memory.cycle_count(conn)} terminé ({mode}).")
    print(f"   Initiatives lancées : {len(selected)} | Nouveaux agents : {len(new_agents)}")
    print(f"   Données : {intake.get('source')} | LLM : {llm.status()}")
    print(f"   Brief CEO : {os.path.relpath(path, ROOT)}")
    print(f"   File d'approbation : {len(memory.list_approvals(conn))} décision(s) ROUGE en attente.")
    print(f"   Compteur exclusion de données : {memory.total_exclusion_attempts(conn)} (cible 0)")
    conn.close()


# ----------------------------------------------------------------------
#  CLI
# ----------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description="Orchestrateur de l'entreprise IA (Agent CEO).")
    p.add_argument("--cycle", action="store_true", help="exécute un cycle de gestion complet")
    p.add_argument("--bootstrap", action="store_true", help="initialise la DB + synchronise les agents")
    p.add_argument("--dry-run", dest="dry_run", action="store_true", default=True,
                   help="aucun effet de bord externe (défaut)")
    p.add_argument("--live", dest="dry_run", action="store_false",
                   help="désactive le dry-run (exécution réelle)")
    p.add_argument("--new-initiative", metavar="IDEE", help="injecte une idée dans l'INTAKE")
    p.add_argument("--spawn-agent", metavar="BESOIN", help="invoque l'Agent Factory")
    p.add_argument("--approve", type=int, metavar="ID", help="approuve une décision en file")
    p.add_argument("--reject", type=int, metavar="ID", help="rejette une décision en file")
    p.add_argument("--pause", action="store_true", help="active le kill switch")
    p.add_argument("--resume", action="store_true", help="désactive le kill switch")
    p.add_argument("--brief", action="store_true", help="(re)génère le brief CEO")
    p.add_argument("--org", action="store_true", help="affiche organigramme + agents + KPI")
    args = p.parse_args()

    if args.bootstrap:
        conn = memory.connect()
        n = sync_agents(conn)
        print(f"✅ Bootstrap : DB initialisée, {n} agent(s) synchronisé(s).")
        conn.close()
        return
    if args.pause:
        memory.set_state_flag("PAUSED"); print("⏸️  STATE = PAUSED"); return
    if args.resume:
        memory.set_state_flag("RUNNING"); print("▶️  STATE = RUNNING"); return
    if args.new_initiative:
        conn = memory.connect()
        clean, blocked = G.filter_excluded(conn, [args.new_initiative])
        if blocked:
            print(f"🚫 Idée bloquée (exclusion de données) : {blocked}")
        else:
            iid = memory.add_initiative(conn, args.new_initiative,
                                        "Hypothèse fournie par l'opérateur.",
                                        "Injectée via /new-initiative.")
            print(f"✅ Initiative #{iid} ajoutée à l'INTAKE.")
        conn.close(); return
    if args.spawn_agent:
        conn = memory.connect()
        res = factory.create_agent(conn, args.spawn_agent)
        print(f"🧬 Agent Factory : {res}")
        conn.close(); return
    if args.approve is not None or args.reject is not None:
        conn = memory.connect()
        aid = args.approve if args.approve is not None else args.reject
        decision = "approved" if args.approve is not None else "rejected"
        row = memory.resolve_approval(conn, aid, decision, resolved_by="human")
        print(f"{'✅' if decision=='approved' else '❌'} Approbation #{aid} -> {decision}"
              if row else f"⚠️  Aucune entrée #{aid} en file.")
        conn.close(); return
    if args.org:
        conn = memory.connect(); sync_agents(conn)
        print("=== ORGANIGRAMME & AGENTS ===")
        for a in memory.list_agents(conn, status=None):
            print(f"  [{a['status']:>11}] {a['name']:<22} score={a['performance_score']:.2f}"
                  f"  (par {a['created_by']})")
        print("\n=== KPI ===")
        for m in memory.latest_metrics(conn):
            print(f"  {m['name']:<22} {m['value']:g}{m['unit']}  (cible {m['target']:g})")
        print(f"\nExclusions: total tentatives = {memory.total_exclusion_attempts(conn)} (cible 0)")
        print("\n=== INTÉGRATIONS ===")
        print(f"  LLM     : {llm.status()}")
        print(f"  Shopify : {shopify.status()}")
        live = os.environ.get('COMPANY_ALLOW_LIVE') == '1'
        print(f"  Mode    : {'LIVE autorisé' if live else 'dry-run (réel verrouillé)'}")
        conn.close(); return
    if args.brief:
        conn = memory.connect()
        cid = memory.cycle_count(conn)
        path = reporting.write_brief(conn, cid, "manual-brief",
                                     budget_caps=(CYCLE_CAP, GLOBAL_CAP), dry_run=True)
        print(f"✅ Brief régénéré : {os.path.relpath(path, ROOT)}")
        conn.close(); return
    if args.cycle:
        # Garde-fou de passage en réel : --live exige une autorisation explicite
        # et durable (COMPANY_ALLOW_LIVE=1), sinon on refuse et on explique.
        if not args.dry_run and os.environ.get("COMPANY_ALLOW_LIVE") != "1":
            print("🛑 Mode --live demandé mais non autorisé.")
            print("   Le réel engage des coûts (appels LLM/API) et des effets externes.")
            print("   Pour autoriser : export COMPANY_ALLOW_LIVE=1, puis relancer.")
            print("   Rappel : les actions ROUGE restent TOUJOURS en file d'approbation.")
            return
        run_cycle(dry_run=args.dry_run); return

    p.print_help()


if __name__ == "__main__":
    main()
