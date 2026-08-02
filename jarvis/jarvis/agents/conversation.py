"""ConversationOrchestrator v0 — gère les conversations avec des prospects.

État machine :
  cold → engaged → qualifying → hot → (won|lost) | cold_opt_out
Transitions gouvernées par signaux détectés (réponse, silence, opt-out, demande
démo, question pricing, etc.).

Garde-fous :
  - max 3 messages sans réponse
  - max 2 relances
  - break-up obligatoire à la 2e relance sans retour
  - opt-out universel multi-langue
  - heures d'envoi respectées par zone
  - voice lint sur chaque draft avant envoi
  - niveau autonomie 1 (propose) tant que evals < 0.9 sur la zone
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from jarvis.agents.base import AgentBase, AgentCharter, AutonomyLevel
from jarvis.core.scope import ScopeFilter
from jarvis.observability.audit import audit
from jarvis.voice.lint import VoiceLint
from jarvis.voice.zones import Zone, zone_profile

Channel = Literal["email", "linkedin", "whatsapp", "telegram", "sms"]


class ConvState(str, Enum):
    COLD = "cold"
    ENGAGED = "engaged"
    QUALIFYING = "qualifying"
    HOT = "hot"
    WON = "won"
    LOST = "lost"
    OPT_OUT = "cold_opt_out"


# Opt-out patterns multi-langue. Lookup simple, assez robuste pour Phase 1.2.
_OPT_OUT_PATTERNS = [
    r"\bstop\b",
    r"\bunsubscribe\b",
    r"\bd[ée]sabonne(r|z)?\b",
    r"\barr[eê]te(z|r)?\b",
    r"\blaisse(r|z)? tomber\b",
    r"\bno thanks\b",
    r"\bnot interested\b",
    r"\bpas int[eé]ress[eé]e?\b",
    r"\bne plus me contacter\b",
    r"\bremove me\b",
    r"\bretire(z|r)? moi\b",
]
_OPT_OUT_RE = [re.compile(p, re.IGNORECASE) for p in _OPT_OUT_PATTERNS]


def detect_opt_out(text: str) -> bool:
    return any(p.search(text) for p in _OPT_OUT_RE)


# Signaux chauds
_HOT_PATTERNS = [
    r"\bdemo\b", r"\bd[ée]mo\b",
    r"\bpricing\b", r"\btarif\b",
    r"\bcombien (ça|ca) co[uû]te\b",
    r"\bquand peut[- ]on parler\b",
    r"\bsend me\b.*\bmore\b",
    r"\bappel(l|)ons\b",
]
_HOT_RE = [re.compile(p, re.IGNORECASE) for p in _HOT_PATTERNS]


def detect_hot_signal(text: str) -> bool:
    return any(p.search(text) for p in _HOT_RE)


@dataclass
class Conversation:
    id: str
    subject_id: str
    venture: str
    zone: str
    channel: Channel
    state: ConvState = ConvState.COLD
    last_message_at: float | None = None
    messages_sent: int = 0
    relances_count: int = 0
    opt_out: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    memory_ref: str | None = None

    def to_row(self) -> dict[str, Any]:
        d = asdict(self)
        d["state"] = self.state.value
        return d


@dataclass
class MessageDecision:
    allow: bool
    reason: str
    next_state: ConvState | None = None
    should_break_up: bool = False


class ConversationOrchestrator(AgentBase):
    def __init__(
        self,
        scope: ScopeFilter,
        *,
        lint: VoiceLint | None = None,
        clock=None,  # injection pour tests
    ) -> None:
        super().__init__(
            AgentCharter(
                name="ConversationOrchestrator",
                venture="jonction",
                zone="FR",
                human_facing=True,
                mission=(
                    "Gère conversations prospects multi-canal, multi-tours. "
                    "État, ton adapté zone, opt-out sacré, frequency cap strict, "
                    "escalade humain sur signal chaud."
                ),
                autonomy=AutonomyLevel.PROPOSE,
                eval_threshold=0.9,
            )
        )
        self._scope = scope
        self._lint = lint or VoiceLint()
        self._clock = clock or time.time

    def can_send(self, conv: Conversation) -> MessageDecision:
        if conv.opt_out:
            return MessageDecision(False, "opt_out")
        if conv.state == ConvState.OPT_OUT:
            return MessageDecision(False, "state_opt_out")
        if conv.relances_count >= 2 and conv.state == ConvState.COLD:
            # 3e relance interdite. Break-up obligatoire.
            return MessageDecision(False, "frequency_cap_break_up_required", should_break_up=True)
        if conv.messages_sent >= 3 and conv.state == ConvState.COLD:
            return MessageDecision(False, "too_many_unanswered")
        if not self._within_send_hours(conv.zone):
            return MessageDecision(False, "outside_send_hours")
        return MessageDecision(True, "ok")

    def _within_send_hours(self, zone_code: str) -> bool:
        z: Zone = zone_profile(zone_code)
        now = datetime.now(timezone.utc)
        # Approximation : heure UTC + offset moyen zone. Jalon 1.3 branchera un
        # calcul précis via pytz/timezonefinder.
        offsets = {
            "FR": 1, "DACH": 1, "IT": 1, "ES": 1, "PT": 0, "BENELUX": 1,
            "UK": 0, "NORDICS": 1, "US": -5, "CA": -5, "JP": 9, "KR": 9, "CN": 8,
        }
        offset = offsets.get(z.code, 0)
        local_hour = (now.hour + offset) % 24
        weekday = now.weekday()  # 0 lundi → 6 dimanche
        if weekday >= 5:
            return False
        lo, hi = z.send_hours_local
        return lo <= local_hour < hi

    def observe_inbound(self, conv: Conversation, text: str) -> Conversation:
        """Reçoit un message entrant, met à jour l'état."""
        if detect_opt_out(text):
            conv.opt_out = True
            conv.state = ConvState.OPT_OUT
            audit("conversation.opt_out", conv_id=conv.id, subject=conv.subject_id)
        elif detect_hot_signal(text):
            conv.state = ConvState.HOT
            audit("conversation.hot_signal", conv_id=conv.id, subject=conv.subject_id)
        elif conv.state == ConvState.COLD:
            conv.state = ConvState.ENGAGED
        conv.relances_count = 0  # réponse reçue = reset cap
        conv.updated_at = self._clock()
        return conv

    def record_outbound(self, conv: Conversation, is_relance: bool = False) -> Conversation:
        conv.messages_sent += 1
        if is_relance:
            conv.relances_count += 1
        conv.last_message_at = self._clock()
        conv.updated_at = self._clock()
        return conv

    def prepare_draft(
        self,
        conv: Conversation,
        draft_text: str,
        first_name_hint: str | None = None,
    ) -> tuple[bool, str, list[str]]:
        """Retourne (ok, texte, issues). Bloque si lint hard KO ou scope KO."""
        try:
            self._scope.assert_clean(draft_text, source="conversation_draft")
        except Exception as e:
            audit("conversation.scope_block", conv_id=conv.id, detail=str(e))
            return False, "[BLOCKED scope]", ["scope_violation"]
        lint = VoiceLint(first_name_hint=first_name_hint).check(draft_text)
        if lint.hard_issues:
            audit(
                "conversation.voice_block",
                conv_id=conv.id,
                rules=[i.rule for i in lint.hard_issues],
                score=lint.score,
            )
            return False, draft_text, [i.rule for i in lint.hard_issues]
        return True, draft_text, []

    def break_up_message(self, conv: Conversation, first_name: str) -> str:
        """Message de clôture courtois avant stop définitif."""
        return (
            f"Salut {first_name},\n\n"
            "Je te laisse tranquille. Si un jour le sujet revient, tu sais où me trouver.\n\n"
            "— Laurent"
        )

    @staticmethod
    def new(
        subject_id: str, venture: str, zone: str, channel: Channel = "email"
    ) -> Conversation:
        return Conversation(
            id=str(uuid.uuid4()),
            subject_id=subject_id,
            venture=venture,
            zone=zone,
            channel=channel,
        )
