"""Jarvis orchestrateur — Router → Planner → Dispatcher → Aggregator → Verifier.

Phase 1.1 : squelette. Le pipeline complet arrive en Phase 1.2.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jarvis.agents.base import AgentBase, AgentCharter, AutonomyLevel
from jarvis.core.scope import ScopeFilter


@dataclass
class Intent:
    raw: str
    venture: str | None = None
    zone: str | None = None


class JarvisOrchestrator(AgentBase):
    def __init__(self, scope: ScopeFilter) -> None:
        super().__init__(
            AgentCharter(
                name="Jarvis",
                venture="transverse",
                zone="FR",
                human_facing=True,
                mission=(
                    "Orchestrateur. Comprend l'intention de Laurent, choisit le "
                    "bon spécialiste ou demande au Builder d'en créer un. "
                    "Traduit les résultats en actions, pose des questions "
                    "seulement si bloqué. Format rapport Telegram imposé."
                ),
                autonomy=AutonomyLevel.PROPOSE,
            )
        )
        self._scope = scope

    async def classify(self, text: str) -> Intent:
        self._scope.assert_clean(text, source="jarvis_intent")
        return Intent(raw=text)

    async def handle(self, text: str) -> dict[str, Any]:
        """Phase 1.1 stub. Route naïvement vers 'echo'."""
        intent = await self.classify(text)
        return {"intent": intent.raw, "action": "noop", "reason": "phase_1_1_stub"}
