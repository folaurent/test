"""AgentBase — socle commun de tous les spécialistes.

Garanties :
  - Périmètre : préfixe SCOPE_SYSTEM_PREFIX injecté dans chaque system prompt.
  - Voix : si agent en contact humain, préfixe voice_system_prompt() injecté.
  - Évals : chaque agent a ses golden tasks. Autonomie bloquée sans eval.
  - Autonomie : niveau 0 (shadow) → 1 (propose) → 2 (agit avec frein) → 3 (auto).
  - Budget : passe par BudgetManager avant appel LLM.
  - Audit : chaque action est logguée.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

from jarvis.core.scope import SCOPE_SYSTEM_PREFIX
from jarvis.voice.dna import voice_system_prompt


class AutonomyLevel(IntEnum):
    SHADOW = 0     # observe, ne fait rien
    PROPOSE = 1    # propose, humain valide
    ACT_SAFE = 2   # agit sur actions réversibles/à faible impact
    ACT_FULL = 3   # agit plein périmètre (jamais atteint par défaut)


@dataclass
class AgentCharter:
    name: str
    mission: str
    venture: str  # "transverse" pour Jarvis/Builder/Compliance
    zone: str = "FR"
    human_facing: bool = False
    autonomy: AutonomyLevel = AutonomyLevel.SHADOW
    model_tiers: dict[str, str] = field(default_factory=dict)  # task_kind → tier
    tool_allowlist: list[str] = field(default_factory=list)
    budget_eur_month: float = 0.0
    budget_tokens_month: int = 0
    budget_user_questions_day: int = 0
    eval_threshold: float = 0.9  # seuil pour promouvoir autonomie
    playbooks_dir: str = ""
    probation_until: float | None = None  # timestamp fin probation 30j
    pii_policy: str = "minimize"  # minimize | collect_consented | forbidden


class AgentBase:
    def __init__(self, charter: AgentCharter) -> None:
        self.charter = charter
        self._system_prompt_cache: str | None = None

    def system_prompt(self) -> str:
        if self._system_prompt_cache is not None:
            return self._system_prompt_cache
        parts: list[str] = [SCOPE_SYSTEM_PREFIX]
        if self.charter.human_facing:
            parts.append(voice_system_prompt(self.charter.name, self.charter.zone))
        parts.append(f"[RÔLE] {self.charter.mission}")
        parts.append(
            f"[AUTONOMIE] Niveau {int(self.charter.autonomy)}. "
            f"Tu ne dépasses jamais ce niveau sans validation explicite Telegram."
        )
        if self.charter.tool_allowlist:
            parts.append(
                "[OUTILS AUTORISÉS] " + ", ".join(self.charter.tool_allowlist) +
                ". Tout appel hors liste = refus + scope_violation."
            )
        self._system_prompt_cache = "\n\n".join(parts)
        return self._system_prompt_cache

    def assert_tool_allowed(self, tool: str) -> None:
        if self.charter.tool_allowlist and tool not in self.charter.tool_allowlist:
            raise PermissionError(
                f"{self.charter.name}: tool '{tool}' hors allowlist"
            )

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.charter.name,
            "venture": self.charter.venture,
            "zone": self.charter.zone,
            "autonomy": int(self.charter.autonomy),
            "human_facing": self.charter.human_facing,
            "tools": self.charter.tool_allowlist,
        }
