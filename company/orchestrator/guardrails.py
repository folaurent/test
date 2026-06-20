"""
guardrails.py — classification des actions + plafonds + exclusions (§10).

Taxonomie (classée AVANT toute exécution) :
  🟢 GREEN — réversible, interne, sans coût           -> autonome
  🟡 AMBER — réversible, externe ou faible coût        -> autonome dans le budget + journalisé
  🔴 RED   — irréversible / coûteux / légal / réel     -> STOP + approvals_queue, jamais exécuté

Exclusion de données = double verrou :
  (1) à l'INTAKE  : filter_excluded() retire/bloque tout item touchant une entité interdite
  (2) à l'EXECUTE : assert_clean() re-vérifie avant action
Toute tentative incrémente attempted_access_count ET lève une alerte. Cible : compteur = 0.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import memory

GREEN, AMBER, RED = "GREEN", "AMBER", "RED"


# ----------------------------------------------------------------------
#  Classification
# ----------------------------------------------------------------------
# Mots-clés déclencheurs ROUGE : tout ce qui touche le monde réel,
# l'argent, le légal, l'irréversible, la communication externe, la publication.
RED_KEYWORDS = [
    "send_email", "envoi email", "email client", "publish", "publier", "post ",
    "tweet", "payment", "paiement", "virement", "wire", "charge", "invoice client",
    "sign ", "signature", "contract", "contrat", "delete", "supprimer", "drop ",
    "deploy prod", "production deploy", "refund", "purchase order", "place order",
    "go live", "send sms", "call customer", "appel client",
]
# Mots-clés AMBRE : externe mais réversible / faible coût sous plafond.
AMBER_KEYWORDS = [
    "api call", "appel api", "paid api", "api payante", "scrape", "fetch url",
    "write test db", "base de test", "notify", "slack", "telegram", "draft email",
    "brouillon email", "search web", "llm call",
]


@dataclass
class Verdict:
    action_class: str
    reversible: bool
    reasons: list = field(default_factory=list)
    requires_human: bool = False
    blocked: bool = False  # True si exclusion de données -> action interdite


def classify(action: str, explicit_class: str | None = None,
             cost: float = 0.0) -> Verdict:
    """Classe une action décrite en texte libre (ou via classe explicite)."""
    text = (action or "").lower()
    reasons = []

    # Une classe explicite fournie par l'agent prime, mais ne peut pas
    # DÉCLASSER un signal ROUGE détecté (sécurité par défaut).
    cls = None
    if any(k in text for k in RED_KEYWORDS) or cost >= 0:
        pass  # évaluation détaillée ci-dessous

    if any(k in text for k in RED_KEYWORDS):
        cls = RED
        reasons.append("Mot-clé à conséquence réelle / irréversible détecté.")
    elif any(k in text for k in AMBER_KEYWORDS) or cost > 0:
        cls = AMBER
        reasons.append("Action externe ou à faible coût (sous plafond).")
    else:
        cls = GREEN
        reasons.append("Action interne, réversible, sans coût.")

    # La classe explicite peut DURCIR (jamais adoucir) la classification.
    order = {GREEN: 0, AMBER: 1, RED: 2}
    if explicit_class in order and order[explicit_class] > order[cls]:
        cls = explicit_class
        reasons.append(f"Classe durcie par l'agent -> {explicit_class}.")

    reversible = cls != RED
    requires_human = cls == RED
    return Verdict(action_class=cls, reversible=reversible,
                   reasons=reasons, requires_human=requires_human)


# ----------------------------------------------------------------------
#  Exclusion de données (double verrou)
# ----------------------------------------------------------------------
def _excluded_entities(conn):
    return [e["forbidden_entity"] for e in memory.exclusions(conn)]


def _matches(text: str, entity: str) -> bool:
    # Match insensible à la casse, sur frontière de mot.
    return re.search(rf"\b{re.escape(entity)}\b", text or "", flags=re.IGNORECASE) is not None


def scan_for_exclusions(conn, text: str) -> list:
    """Retourne la liste des entités interdites trouvées dans le texte."""
    return [e for e in _excluded_entities(conn) if _matches(text, e)]


def filter_excluded(conn, items: list, actor="chief-of-staff") -> tuple:
    """
    VERROU 1 (INTAKE). Sépare les items propres des items contaminés.
    Tout item contaminé incrémente le compteur, est journalisé et écarté.
    Retourne (clean_items, blocked_items).
    """
    clean, blocked = [], []
    for item in items:
        text = item if isinstance(item, str) else str(item)
        hits = scan_for_exclusions(conn, text)
        if hits:
            for h in hits:
                memory.bump_exclusion(conn, h)
            memory.audit(conn, actor, "DATA_EXCLUSION_BLOCKED_INTAKE",
                         {"item": text, "entities": hits}, action_class=RED, reversible=False)
            blocked.append({"item": text, "entities": hits})
        else:
            clean.append(item)
    return clean, blocked


def assert_clean(conn, text: str, actor: str) -> bool:
    """
    VERROU 2 (EXECUTE). Re-vérifie juste avant l'action.
    Retourne True si propre, False si contaminé (et bloque + compte + alerte).
    """
    hits = scan_for_exclusions(conn, text)
    if hits:
        for h in hits:
            memory.bump_exclusion(conn, h)
        memory.audit(conn, actor, "DATA_EXCLUSION_BLOCKED_EXECUTE",
                     {"text": text, "entities": hits}, action_class=RED, reversible=False)
        return False
    return True


# ----------------------------------------------------------------------
#  Budget — hard stop au dépassement
# ----------------------------------------------------------------------
class BudgetExceeded(Exception):
    pass


def check_budget(conn, period: str, prospective_cost: float, cap: float) -> bool:
    """Retourne True si la dépense reste sous le plafond, sinon hard stop."""
    b = memory.get_budget(conn, period)
    spent = b["spent"] if b else 0.0
    if spent + prospective_cost > cap:
        memory.audit(conn, "guardrails", "BUDGET_HARD_STOP",
                     {"period": period, "spent": spent, "cost": prospective_cost, "cap": cap},
                     action_class=RED, reversible=False)
        return False
    return True


# ----------------------------------------------------------------------
#  Kill switch
# ----------------------------------------------------------------------
def is_paused() -> bool:
    return memory.get_state_flag() == "PAUSED"


# ----------------------------------------------------------------------
#  Gate unique d'exécution d'action — point de passage obligé (EXECUTE)
# ----------------------------------------------------------------------
def gate_action(conn, actor: str, action: str, payload=None,
                explicit_class: str | None = None, cost: float = 0.0,
                cycle_period: str = "cycle:0", cycle_cap: float = 10.0,
                global_cap: float = 100.0, dry_run: bool = True) -> dict:
    """
    Le seul chemin par lequel une action peut être 'exécutée'.
    Renvoie un dict décrivant le sort de l'action :
      executed | queued (RED) | blocked_exclusion | blocked_budget | blocked_paused
    En dry-run, aucune action externe n'est réellement effectuée.
    """
    # 0. kill switch
    if is_paused():
        memory.audit(conn, actor, "SKIPPED_PAUSED", {"action": action}, action_class=GREEN)
        return {"outcome": "blocked_paused", "action": action}

    # 1. exclusion de données (verrou 2)
    blob = f"{action} {payload if payload is not None else ''}"
    if not assert_clean(conn, blob, actor):
        return {"outcome": "blocked_exclusion", "action": action}

    # 2. classification
    v = classify(action, explicit_class=explicit_class, cost=cost)

    # 3. ROUGE -> file d'approbation, JAMAIS exécuté
    if v.action_class == RED:
        did = memory.add_decision(conn, context=action, options=["execute", "skip"],
                                  chosen="await_human", rationale="; ".join(v.reasons),
                                  decided_by=actor, action_class=RED, requires_human=True)
        memory.enqueue_approval(conn, did, summary=action, risk_level="RED")
        memory.audit(conn, actor, "QUEUED_FOR_APPROVAL", {"action": action, "decision_id": did},
                     action_class=RED, reversible=False)
        return {"outcome": "queued", "action": action, "decision_id": did}

    # 4. AMBRE -> vérifie le budget (cycle + global)
    if v.action_class == AMBER and cost > 0:
        if not check_budget(conn, cycle_period, cost, cycle_cap):
            return {"outcome": "blocked_budget", "scope": "cycle", "action": action}
        if not check_budget(conn, "global", cost, global_cap):
            return {"outcome": "blocked_budget", "scope": "global", "action": action}
        if not dry_run:
            memory.add_spend(conn, cycle_period, cost, cycle_cap)
            memory.add_spend(conn, "global", cost, global_cap)
        else:
            memory.audit(conn, actor, "DRY_RUN_NO_SPEND", {"action": action, "would_cost": cost},
                         action_class=AMBER)

    # 5. exécution (GREEN, ou AMBRE sous budget)
    memory.audit(conn, actor, f"EXECUTED_{v.action_class}", {"action": action, "payload": payload},
                 action_class=v.action_class, reversible=v.reversible)
    return {"outcome": "executed", "action": action, "action_class": v.action_class}
