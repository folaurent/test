"""Builder v0 — meta-agent qui provisionne des spécialistes à partir d'intentions.

Pipeline (v0 — squelette) :
  1. Parse intention NL → objectif, venture, zone, scope, KPIs suggérés.
  2. Research préalable (via Research, hors scope v0).
  3. Draft plan de provisioning : charte, budgets, evals à produire,
     playbooks, outils, modèles, compliance à valider.
  4. Validation Telegram (boutons ✅/✏️/❌).
  5. Exécution : PR git signé, tests, deploy blue/green, smoke tests.
  6. Handoff au spécialiste avec probation 30j.

Phase 1.1 livre les étapes 1 + 3 + format de plan. Les étapes 4-6 sont
plumbed mais non actives tant que Telegram/git signing/CI ne sont pas
opérationnels.
"""
from __future__ import annotations

import hashlib
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from jarvis.agents.base import AgentBase, AgentCharter, AutonomyLevel
from jarvis.core.scope import SCOPE_SYSTEM_PREFIX, ScopeError, ScopeFilter
from jarvis.observability.audit import audit
from jarvis.voice.zones import zone_profile


@dataclass
class ProvisioningPlan:
    plan_id: str
    intent: str
    summary: str
    new_agents: list[dict[str, Any]] = field(default_factory=list)
    new_tools: list[str] = field(default_factory=list)
    goldens_to_create: int = 0
    zones_touched: list[str] = field(default_factory=list)
    ventures_touched: list[str] = field(default_factory=list)
    estimated_cost_eur_month: float = 0.0
    compliance_checks: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    rollback_strategy: str = "blue_green + auto-revert si smoke KO"
    approvals_required: list[str] = field(default_factory=lambda: ["laurent_telegram"])
    created_at: float = field(default_factory=time.time)

    def as_telegram_card(self) -> str:
        agents = "\n".join(f"  • {a['name']} ({a['venture']}/{a['zone']})" for a in self.new_agents)
        zones = ", ".join(self.zones_touched) or "-"
        ventures = ", ".join(self.ventures_touched) or "-"
        comp = "\n".join(f"  ✔ {c}" for c in self.compliance_checks) or "  (aucun)"
        risks = "\n".join(f"  ⚠ {r}" for r in self.risks) or "  (aucun détecté)"
        return (
            f"🧱 *Plan provisioning* `{self.plan_id[:8]}`\n\n"
            f"*Intention* : {self.intent}\n"
            f"*Résumé* : {self.summary}\n\n"
            f"*Ventures* : {ventures}\n"
            f"*Zones* : {zones}\n\n"
            f"*Nouveaux agents*\n{agents or '  (aucun)'}\n\n"
            f"*Golden tasks à produire* : {self.goldens_to_create}\n"
            f"*Coût estimé* : {self.estimated_cost_eur_month:.0f} €/mois\n\n"
            f"*Compliance*\n{comp}\n\n"
            f"*Risques*\n{risks}\n\n"
            f"*Rollback* : {self.rollback_strategy}\n"
        )


# Heuristiques rapides pour déduire venture/zone depuis le NL. Sera remplacé
# par une classification LLM en Phase 1.3.
_VENTURE_KEYWORDS = {
    "jonction": ["jonction", "btp", "chantier", "carreleur", "carrelage", "artisan"],
    "deco_pro": ["deco", "déco", "pattom", "e-commerce", "sav"],
    "perso": ["perso", "personnel", "famille"],
}

_ZONE_KEYWORDS = {
    "DACH": ["allemagne", "germany", "suisse", "autriche", "dach", "deutsch"],
    "UK": ["uk", "royaume-uni", "angleterre", "britain", "london"],
    "US": ["us", "états-unis", "usa", "amérique"],
    "IT": ["italie", "italia", "italy"],
    "ES": ["espagne", "españa", "spain"],
    "NORDICS": ["suède", "norvège", "danemark", "finlande", "nordic"],
    "BENELUX": ["belgique", "pays-bas", "netherlands", "luxembourg", "benelux"],
    "JP": ["japon", "japan"],
    "FR": ["france", "français", "paris", "lyon", "lille"],
}


class Builder(AgentBase):
    def __init__(self, scope: ScopeFilter) -> None:
        super().__init__(
            AgentCharter(
                name="Builder",
                venture="transverse",
                zone="FR",
                human_facing=False,
                mission=(
                    "Meta-agent. Traduit une intention en langage naturel en "
                    "plan de provisioning vérifiable, orchestre la construction "
                    "(spécialistes, tools, playbooks, evals, compliance), avec "
                    "probation 30 jours. Ne supprime jamais sans double "
                    "confirmation. Ne dépasse jamais le budget infra mensuel. "
                    "Tout changement = PR git signé."
                ),
                autonomy=AutonomyLevel.PROPOSE,
                tool_allowlist=[
                    "git.commit_signed", "git.pr_open", "migration.apply",
                    "deploy.blue_green", "smoke.run", "rollback",
                    "research.query", "eval.run",
                ],
            )
        )
        self._scope = scope

    def parse_intent(self, intent: str) -> dict[str, Any]:
        self._scope.assert_clean(intent, source="builder_intent")
        low = intent.lower()
        venture = next(
            (v for v, kw in _VENTURE_KEYWORDS.items() if any(k in low for k in kw)),
            "jonction",
        )
        zone = next(
            (z for z, kw in _ZONE_KEYWORDS.items() if any(k in low for k in kw)),
            "FR",
        )
        kind = self._classify_kind(low)
        return {"intent": intent, "venture": venture, "zone": zone, "kind": kind}

    def _classify_kind(self, text: str) -> str:
        if any(w in text for w in ("attaque", "lance", "ouvre", "expansion")):
            return "new_zone"
        if any(w in text for w in ("automatise", "automatiser")):
            return "new_automation"
        if any(w in text for w in ("trouve", "sourcer", "prospection")):
            return "new_sourcing_campaign"
        if any(w in text for w in ("engage", "conversation", "relance")):
            return "new_outreach"
        return "generic"

    def draft_plan(self, intent: str) -> ProvisioningPlan:
        parsed = self.parse_intent(intent)
        plan_id = str(uuid.uuid4())
        zone = parsed["zone"]
        venture = parsed["venture"]
        kind = parsed["kind"]

        new_agents: list[dict[str, Any]] = []
        compliance: list[str] = []
        risks: list[str] = []
        goldens = 10

        zp = zone_profile(zone)

        if kind == "new_zone":
            new_agents.extend(
                [
                    {"name": f"Prospection-{zone}", "venture": venture, "zone": zone},
                    {"name": f"Conversation-{zone}", "venture": venture, "zone": zone},
                ]
            )
            goldens = 20
            compliance.extend(
                [
                    f"Validation compliance zone {zone} (base légale + registre art.30)",
                    f"Domaine d'envoi dédié warmup 2 semaines",
                    f"Goldens natifs {zone} validés par natif",
                ]
            )
            if zp.formality in ("high", "very_high"):
                risks.append(
                    f"Zone {zone} très formelle : probation étendue 60j recommandée"
                )
        elif kind == "new_outreach":
            new_agents.append(
                {"name": f"Conversation-{zone}", "venture": venture, "zone": zone}
            )
            compliance.append(
                "Check-list outreach (opt-out, heures locales, frequency cap)"
            )
        elif kind == "new_sourcing_campaign":
            new_agents.append(
                {"name": f"Prospection-{zone}", "venture": venture, "zone": zone}
            )
            compliance.append("Base légale sourcing B2B : intérêt légitime + registre")
        elif kind == "new_automation":
            new_agents.append(
                {"name": f"Ops-{venture}", "venture": venture, "zone": zone}
            )

        est = 15.0 * len(new_agents) + 5.0
        plan = ProvisioningPlan(
            plan_id=plan_id,
            intent=intent,
            summary=f"{kind.replace('_', ' ')} | venture={venture} zone={zone}",
            new_agents=new_agents,
            new_tools=[],
            goldens_to_create=goldens,
            zones_touched=[zone],
            ventures_touched=[venture],
            estimated_cost_eur_month=est,
            compliance_checks=compliance,
            risks=risks,
        )
        audit(
            "builder.plan_drafted",
            plan_id=plan_id,
            venture=venture,
            zone=zone,
            kind=kind,
            cost_eur=est,
        )
        return plan

    def plan_fingerprint(self, plan: ProvisioningPlan) -> str:
        blob = str(sorted(asdict(plan).items()))
        return hashlib.sha256(blob.encode()).hexdigest()[:12]
