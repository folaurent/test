"""
reporting.py — génération du brief CEO + tableau de bord (§11).

À chaque cycle, écrit /reports/<horodatage>.md avec :
  - état des initiatives & résultats vs KPI
  - tableau de bord metrics vs cibles
  - file d'approbation (décisions ROUGE en attente + recommandation)
  - nouveaux agents créés ce cycle
  - top 3 leçons
  - compteur d'exclusion de données (doit afficher 0)
  - alertes budget
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import memory
import notify

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(ROOT, "reports")


def _kpi_arrow(value, target):
    if target in (None, 0):
        return "—"
    if value >= target:
        return "✅"
    if value >= 0.7 * target:
        return "🟡"
    return "🔴"


def build_brief(conn, cycle_id, mode, new_agents=None, budget_caps=(10.0, 100.0)) -> str:
    new_agents = new_agents or []
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cycle_no = memory.cycle_count(conn)
    excl_total = memory.total_exclusion_attempts(conn)
    cycle_cap, global_cap = budget_caps

    inits = memory.list_initiatives(conn)
    running = [i for i in inits if i["status"] == "running"]
    closed = [i for i in inits if i["status"] == "closed"]
    planned = [i for i in inits if i["status"] in ("planned", "proposed")]

    approvals = memory.list_approvals(conn, "pending")
    metrics = memory.latest_metrics(conn)
    lessons = memory.recent_lessons(conn, 3)

    gb = memory.get_budget(conn, "global")
    cb = memory.get_budget(conn, f"cycle:{cycle_id}")
    global_spent = gb["spent"] if gb else 0.0
    cycle_spent = cb["spent"] if cb else 0.0

    L = []
    L.append(f"# 🧠 Brief CEO — Cycle #{cycle_no}")
    L.append("")
    L.append(f"- **Date** : {ts}")
    L.append(f"- **Mode** : `{mode}`")
    L.append(f"- **Kill switch** : `{memory.get_state_flag()}`")
    L.append("")

    # --- Garde-fous en tête (les plus critiques) ---
    L.append("## 🛡️ Garde-fous")
    flag = "✅ 0" if excl_total == 0 else f"🚨 {excl_total}"
    L.append(f"- **Compteur d'exclusion de données** (cible 0) : {flag}")
    for e in memory.exclusions(conn):
        L.append(f"  - `{e['forbidden_entity']}` : {e['attempted_access_count']} tentative(s)")
    bud_cycle = "✅" if cycle_spent <= cycle_cap else "🚨 DÉPASSÉ"
    bud_glob = "✅" if global_spent <= global_cap else "🚨 DÉPASSÉ"
    L.append(f"- **Budget cycle** : {cycle_spent:.2f} / {cycle_cap:.2f} {bud_cycle}")
    L.append(f"- **Budget global** : {global_spent:.2f} / {global_cap:.2f} {bud_glob}")
    L.append("")

    # --- Initiatives ---
    L.append("## 🚀 Initiatives")
    L.append(f"- En cours : **{len(running)}** · Clôturées : **{len(closed)}** · "
             f"Planifiées/proposées : **{len(planned)}**")
    L.append("")
    if inits:
        L.append("| # | Titre | Statut | Priorité | Owner | KPI attendu | Résultat |")
        L.append("|---|-------|--------|----------|-------|-------------|----------|")
        for i in inits[:15]:
            L.append(f"| {i['id']} | {i['title']} | {i['status']} | {i['priority']:.2f} | "
                     f"{i['owner_agent'] or '—'} | {i['expected_kpi'] or '—'} | {i['result'] or '—'} |")
        L.append("")

    # --- Tableau de bord KPI ---
    L.append("## 📊 Tableau de bord (KPI vs cibles)")
    if metrics:
        L.append("| Métrique | Valeur | Cible | Statut |")
        L.append("|----------|--------|-------|--------|")
        for m in metrics:
            L.append(f"| {m['name']} | {m['value']:g} {m['unit'] or ''} | "
                     f"{m['target']:g} | {_kpi_arrow(m['value'], m['target'])} |")
    else:
        L.append("_Aucune métrique enregistrée pour l'instant._")
    L.append("")

    # --- File d'approbation ---
    L.append("## 🔴 File d'approbation (arbitrage humain requis)")
    if approvals:
        L.append("> Ces actions ROUGE sont **bloquées** et n'ont **pas** été exécutées.")
        L.append("")
        L.append("| ID | Risque | Résumé | Recommandation |")
        L.append("|----|--------|--------|----------------|")
        for a in approvals:
            L.append(f"| {a['id']} | {a['risk_level']} | {a['summary']} | "
                     f"À examiner — `/approve {a['id']}` ou `/reject {a['id']}` |")
    else:
        L.append("_Aucune décision en attente._")
    L.append("")

    # --- Nouveaux agents ---
    L.append("## 🧬 Nouveaux agents créés ce cycle")
    if new_agents:
        for a in new_agents:
            L.append(f"- `{a}`")
    else:
        L.append("_Aucun._")
    L.append("")

    # --- Leçons ---
    L.append("## 📚 Top 3 leçons du cycle")
    if lessons:
        for l in lessons:
            L.append(f"- **{l['learning']}** — _{l['observation']}_ → action : {l['action_taken']}")
    else:
        L.append("_Aucune leçon enregistrée._")
    L.append("")

    L.append("---")
    L.append("_Brief généré automatiquement par reporting.py. "
             "Aucune action ROUGE n'est exécutée sans approbation humaine._")
    return "\n".join(L)


def write_brief(conn, cycle_id, mode, new_agents=None, budget_caps=(10.0, 100.0),
                dry_run=True) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    text = build_brief(conn, cycle_id, mode, new_agents, budget_caps)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(REPORTS_DIR, f"{stamp}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    # Connecteur Slack/Telegram (jamais d'envoi réel en dry-run)
    status = notify.push_brief(text, dry_run=dry_run)
    memory.audit(conn, "reporting", "BRIEF_GENERATED",
                 {"path": path, "notify": status}, action_class="GREEN")
    return path
