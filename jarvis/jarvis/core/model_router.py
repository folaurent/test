"""Router de modèles — Haiku / Sonnet / Opus + Ollama fallback.

Règle de routage (intention → tier) :
  router/classification → Haiku 4.5
  planning/rédaction/conversation standard → Sonnet 4.6
  décisions structurelles, compliance, closing VIP → Opus 4.7
  fallback API down non-critique → Ollama Llama 3.3

Usages :
    tier = ModelRouter.choose(task_kind="cold_email_draft")
    model_id = settings.model_for(tier)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from jarvis.core.config import Settings


class Tier(str, Enum):
    ROUTER = "router"
    STANDARD = "standard"
    CRITICAL = "critical"
    FALLBACK = "fallback"


# Map conservatrice : en cas de doute on monte d'un cran, pas l'inverse.
_TASK_TO_TIER: dict[str, Tier] = {
    # router/classification
    "intent_classification": Tier.ROUTER,
    "routing": Tier.ROUTER,
    "triage": Tier.ROUTER,
    "tag_extraction": Tier.ROUTER,
    # planning/standard
    "planning": Tier.STANDARD,
    "cold_email_draft": Tier.STANDARD,
    "conversation_reply": Tier.STANDARD,
    "code_generation": Tier.STANDARD,
    "content_draft": Tier.STANDARD,
    "research_summary": Tier.STANDARD,
    # critical
    "compliance_review": Tier.CRITICAL,
    "builder_structural_decision": Tier.CRITICAL,
    "closing_vip": Tier.CRITICAL,
    "scope_ambiguity_review": Tier.CRITICAL,
    "legal_drafting": Tier.CRITICAL,
}


@dataclass(frozen=True)
class ModelChoice:
    tier: Tier
    model_id: str
    reason: str


class ModelRouter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @classmethod
    def choose_tier(cls, task_kind: str) -> Tier:
        return _TASK_TO_TIER.get(task_kind, Tier.STANDARD)

    def choose(self, task_kind: str, *, fallback: bool = False) -> ModelChoice:
        if fallback:
            return ModelChoice(
                tier=Tier.FALLBACK,
                model_id=self._settings.ollama_fallback_model,
                reason="api_down_fallback",
            )
        tier = self.choose_tier(task_kind)
        model_id = {
            Tier.ROUTER: self._settings.model_router_tier,
            Tier.STANDARD: self._settings.model_standard_tier,
            Tier.CRITICAL: self._settings.model_critical_tier,
        }[tier]
        return ModelChoice(tier=tier, model_id=model_id, reason=task_kind)
