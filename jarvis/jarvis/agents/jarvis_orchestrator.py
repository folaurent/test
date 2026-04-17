"""Jarvis orchestrateur — pipeline complet.

    Router    : classifie l'intention (quel spécialiste ? builder ? refus ?)
    Planner   : décompose en étapes exécutables (pour builder/conversation)
    Dispatcher: envoie sur le bus aux spécialistes
    Aggregator: attend les retours, fusionne
    Verifier  : revérifie scope + voice + facts avant de rendre au user
"""
from __future__ import annotations

import asyncio
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from jarvis.agents.base import AgentBase, AgentCharter, AutonomyLevel
from jarvis.bus.bus import MessageBus
from jarvis.bus.schema import BusEvent, BusMessage
from jarvis.core.scope import ScopeError, ScopeFilter
from jarvis.observability.audit import audit
from jarvis.observability.logger import get_logger
from jarvis.voice.lint import VoiceLint

logger = get_logger(__name__)


class Route(str, Enum):
    META = "meta"         # salutations, self-intro, "que fais-tu", aide
    BUILDER = "builder"
    COMMERCE = "commerce"
    PROSPECTION = "prospection"
    CONVERSATION = "conversation"
    CONTENT = "content"
    FINANCE = "finance"
    RESEARCH = "research"
    DEV = "dev"
    COMMS = "comms"
    TRAVEL = "travel"
    OPS = "ops"
    COMPLIANCE = "compliance"
    REFUSE = "refuse"     # hors scope
    CLARIFY = "clarify"   # ambiguïté bloquante
    NOOP = "noop"


@dataclass
class RoutedIntent:
    raw: str
    route: Route
    venture: str | None = None
    zone: str | None = None
    kind: str | None = None
    reasoning: str = ""


@dataclass
class PlanStep:
    order: int
    agent: str
    action: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    plan_id: str
    intent: RoutedIntent
    steps: list[PlanStep]
    needs_approval: bool = True


# Mots-clefs → route. Router-LLM (Haiku) prendra le relais dès qu'une clef
# Anthropic est dispo ; cette table sert de fallback déterministe et de
# point de comparaison (canary) contre l'overconfidence du LLM.
# Ordre = priorité : les routes les plus spécifiques d'abord.
_ROUTE_KEYWORDS: list[tuple[Route, list[str]]] = [
    # META — salutations, self-intro, aide. Doit passer AVANT tout le reste
    # pour qu'un "salut, que peux-tu faire" ne soit pas happé par un keyword
    # business.
    (Route.META, [
        "salut", "bonjour", "hello", "hey", "coucou", "yo",
        "que peux-tu faire", "que peux tu faire", "qu'est-ce que tu peux faire",
        "qu'est-ce que tu fais", "que fais-tu", "que fais tu",
        "qui es-tu", "qui es tu", "c'est qui",
        "aide", "help", "capacités", "capacites", "fonctionnalités",
        "comment tu marches", "comment ça marche", "comment ca marche",
    ]),
    (Route.CONVERSATION, ["engage la conversation", "relance le", "relance la", "relance les",
                          "cold mail", "cold email"]),
    (Route.COMPLIANCE, ["compliance", "rgpd", "dpa", "légal"]),
    (Route.COMMS, ["mail à", "relance fournisseur", "sav"]),
    (Route.TRAVEL, ["voyage", "billet", "hôtel", "avion"]),
    (Route.DEV, ["bug", "code", "refactor", "migration", "déploie"]),
    (Route.FINANCE, ["coût", "budget", "facture", "compta"]),
    (Route.RESEARCH, ["cherche", "recherche", "étude", "benchmark"]),
    (Route.PROSPECTION, ["trouve", "sourcer", "liste de", "prospects"]),
    (Route.BUILDER, [
        "attaque", "lance", "ouvre", "expansion", "automatise",
        "crée un agent", "provisionne", "nouvelle zone",
    ]),
]


def _kw_hit(text: str, kws: list[str]) -> bool:
    """Match avec frontière de mot pour éviter 'lance' dans 'relance'."""
    for kw in kws:
        if " " in kw:
            if kw in text:
                return True
        else:
            if re.search(rf"\b{re.escape(kw)}\b", text):
                return True
    return False


class JarvisOrchestrator(AgentBase):
    def __init__(
        self,
        scope: ScopeFilter,
        bus: MessageBus | None = None,
        voice_lint: VoiceLint | None = None,
    ) -> None:
        super().__init__(
            AgentCharter(
                name="Jarvis",
                venture="transverse",
                zone="FR",
                human_facing=True,
                mission=(
                    "Orchestrateur. Comprend l'intention de Laurent, route vers "
                    "le bon spécialiste ou demande au Builder d'en créer un. "
                    "Traduit les résultats en actions, pose des questions "
                    "seulement si bloqué."
                ),
                autonomy=AutonomyLevel.PROPOSE,
            )
        )
        self._scope = scope
        self._bus = bus
        self._lint = voice_lint or VoiceLint()

    # ---------- Router ----------
    async def route(self, text: str) -> RoutedIntent:
        try:
            self._scope.assert_clean(text, source="jarvis_router")
        except ScopeError as e:
            audit("scope_violation", source="jarvis_router", detail=str(e))
            return RoutedIntent(raw=text, route=Route.REFUSE, reasoning=str(e))

        low = text.lower()
        for route, kws in _ROUTE_KEYWORDS:
            if _kw_hit(low, kws):
                return RoutedIntent(raw=text, route=route, reasoning=f"kw:{route.value}")
        # Fallthrough : question courte sans keyword business = CLARIFY
        # (mieux que de router à Research au hasard).
        return RoutedIntent(raw=text, route=Route.CLARIFY, reasoning="aucun mot-clef")

    # ---------- Planner ----------
    async def plan(self, intent: RoutedIntent) -> ExecutionPlan:
        plan_id = str(uuid.uuid4())
        steps: list[PlanStep] = []
        if intent.route == Route.META:
            steps.append(PlanStep(1, "Jarvis", "reply_meta", {"raw": intent.raw}))
        elif intent.route == Route.BUILDER:
            steps.append(PlanStep(1, "Builder", "draft_plan", {"intent": intent.raw}))
        elif intent.route == Route.CONVERSATION:
            steps.append(
                PlanStep(1, "ConversationOrchestrator", "draft_message", {"brief": intent.raw})
            )
        elif intent.route == Route.PROSPECTION:
            steps.append(
                PlanStep(1, "Prospection-FR", "source_list", {"brief": intent.raw})
            )
        elif intent.route == Route.RESEARCH:
            steps.append(PlanStep(1, "Research", "answer", {"question": intent.raw}))
        elif intent.route == Route.REFUSE:
            steps.append(PlanStep(1, "Jarvis", "reply_refuse", {"reason": intent.reasoning}))
        elif intent.route == Route.CLARIFY:
            steps.append(PlanStep(1, "Jarvis", "reply_clarify", {"raw": intent.raw}))
        else:
            steps.append(PlanStep(1, "Jarvis", "reply_noop", {"raw": intent.raw}))
        return ExecutionPlan(plan_id=plan_id, intent=intent, steps=steps)

    # ---------- Dispatcher ----------
    async def dispatch(self, plan: ExecutionPlan) -> list[BusMessage]:
        """Émet chaque step sur le bus (si bus branché). Sinon retourne juste la liste."""
        msgs = [
            BusMessage(
                trace_id=plan.plan_id,
                from_agent="Jarvis",
                to_agent=s.agent,
                kind=f"task.{s.action}",
                payload={"step_order": s.order, **s.payload},
            )
            for s in plan.steps
        ]
        if self._bus is not None:
            for m in msgs:
                try:
                    await self._bus.send(m)
                except ScopeError as e:
                    audit("jarvis.dispatch.scope_blocked", trace_id=m.trace_id, detail=str(e))
                    await self._bus.emit(
                        BusEvent(
                            trace_id=m.trace_id, kind="scope_violation",
                            source="jarvis_dispatch", payload={"error": str(e)},
                        )
                    )
        return msgs

    # ---------- Aggregator ----------
    async def aggregate(
        self, plan: ExecutionPlan, timeout_s: float = 30.0
    ) -> dict[str, Any]:
        """En Phase 1.2 : simulateur synchrone quand bus n'est pas branché."""
        if self._bus is None:
            return {"plan_id": plan.plan_id, "mode": "simulated", "steps": len(plan.steps)}
        # En prod : collecter les "result.return" jusqu'à timeout.
        deadline = time.time() + timeout_s
        results: list[BusMessage] = []
        needed = len(plan.steps)
        async for msg in self._bus.subscribe_agent("Jarvis"):
            if msg.trace_id == plan.plan_id and msg.kind == "result.return":
                results.append(msg)
                if len(results) >= needed:
                    break
            if time.time() > deadline:
                break
        return {"plan_id": plan.plan_id, "results": [r.payload for r in results]}

    # ---------- Verifier ----------
    async def verify(self, plan: ExecutionPlan, aggregation: dict[str, Any], final_text: str) -> str:
        try:
            self._scope.assert_clean(final_text, source="jarvis_verify")
        except ScopeError:
            return "[BLOCKED: scope_output]"
        lint = self._lint.check(final_text)
        if lint.hard_issues:
            audit(
                "voice_lint_block", trace_id=plan.plan_id,
                rules=[i.rule for i in lint.hard_issues], score=lint.score,
            )
            return "[BLOCKED: voice_lint " + ",".join(i.rule for i in lint.hard_issues) + "]"
        return final_text

    # ---------- Pipeline entier ----------
    async def handle(self, text: str) -> dict[str, Any]:
        intent = await self.route(text)
        plan = await self.plan(intent)
        await self.dispatch(plan)
        aggregation = await self.aggregate(plan, timeout_s=0.01)
        reply = self._default_reply(intent)
        verified = await self.verify(plan, aggregation, reply)
        return {
            "intent": intent.raw,
            "route": intent.route.value,
            "plan_id": plan.plan_id,
            "steps": [s.__dict__ for s in plan.steps],
            "reply": verified,
        }

    def _default_reply(self, intent: RoutedIntent) -> str:
        if intent.route == Route.REFUSE:
            return (
                "Désolé, je ne peux pas traiter cette demande — elle sort "
                "du périmètre que tu m'as défini."
            )
        if intent.route == Route.META:
            return self._meta_reply()
        if intent.route == Route.CLARIFY:
            return (
                "Pas sûr de ce que tu veux lancer. Dis-moi en une phrase : "
                "prospection ? conversation ? recherche ? automatisation ?"
            )
        # Actions concrètes — on est sans LLM pour l'instant, donc on
        # annonce ce qu'on ferait plutôt que de prétendre exécuter.
        nexts = {
            Route.BUILDER: "Je passe la main au Builder pour draft un plan provisioning.",
            Route.PROSPECTION: "Je route à Prospection-FR pour sourcing.",
            Route.CONVERSATION: "Je passe à ConversationOrchestrator.",
            Route.RESEARCH: "Je route à Research.",
            Route.COMPLIANCE: "Je route à Compliance pour check-list.",
            Route.DEV: "Je route à Dev.",
            Route.FINANCE: "Je route à Finance.",
            Route.COMMS: "Je route à Comms.",
            Route.TRAVEL: "Je route à Travel.",
        }
        tail = nexts.get(intent.route, "Je ne sais pas encore traiter ça directement.")
        return (
            f"Bien reçu. {tail}\n\n"
            "Note : sans clef Anthropic configurée, j'annonce mais je n'exécute "
            "pas encore l'appel LLM — c'est le Jalon 1.3."
        )

    def _meta_reply(self) -> str:
        return (
            "Salut Laurent 👋\n\n"
            "Je suis Jarvis, v6 Phase 1.2. Voici ce que je sais faire aujourd'hui, "
            "et ce qui est encore en chantier.\n\n"
            "*Opérationnel maintenant*\n"
            "• Filtre périmètre des marques exclues verrouillé (double verrou, refus auto)\n"
            "• Voice lint FR (phrases bannies, manipulation, déni d'IA, opt-out)\n"
            "• Routing déterministe par mots-clefs\n"
            "• Builder : `/plan <intention>` → plan de provisioning formalisé\n"
            "• ConversationOrchestrator : state machine + frequency cap + opt-out\n"
            "• Compliance : check-list par zone (FR/DACH/UK/US/CA)\n"
            "• Persistance SQLite locale (bus, queue, memory, audit)\n"
            "• Whitelist Telegram stricte\n\n"
            "*En attente de tes credentials*\n"
            "• Anthropic API key + flag ZDR → active les vrais appels LLM (sinon stub)\n"
            "• Supabase (tu m'as dit de skip pour l'instant — SQLite suffit)\n\n"
            "*Essaie*\n"
            "• `/plan attaque l'Italie` — je te drafte un plan complet\n"
            "• `/voice <texte>` — je te dis si ça passe le lint\n"
            "• `trouve-moi 50 carreleurs à Lyon` — routing Prospection\n"
            "• `automatise le SAV Deco & Pro` — routing Builder\n\n"
            "Dis-moi par où on attaque."
        )
