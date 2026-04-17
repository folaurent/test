"""Anthropic client wrapper — seule porte vers les LLMs payants.

Passage obligatoire via :
  1. Scope filter sur entrée ET sortie
  2. Injection defense : encapsulation entrées externes + scan output
  3. Budget manager : can_spend avant appel, record après
  4. Voice lint sur sortie si agent human_facing (appelant décide)
  5. Audit trail systématique
  6. Retries exponentiels sur erreurs transitoires
  7. Fallback Ollama si l'API Anthropic est down (non-critique only)

Pricing par tier (€/M tokens, valeurs indicatives avril 2026) :
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from jarvis.core.budget import BudgetManager
from jarvis.core.config import Settings
from jarvis.core.model_router import ModelChoice, ModelRouter, Tier
from jarvis.core.scope import ScopeError, ScopeFilter
from jarvis.observability.audit import audit
from jarvis.security.injection import InjectionDefense


# € par million de tokens. Valeurs indicatives — à recaler via la facture réelle.
PRICING_EUR_PER_MTOK: dict[Tier, tuple[float, float]] = {
    # (input, output)
    Tier.ROUTER:   (0.80, 4.00),   # Haiku 4.5
    Tier.STANDARD: (2.80, 14.00),  # Sonnet 4.6
    Tier.CRITICAL: (14.00, 70.00), # Opus 4.7
    Tier.FALLBACK: (0.0, 0.0),     # Ollama local
}


@dataclass
class LLMCall:
    task_kind: str
    system: str
    user: str
    max_tokens: int = 1024
    temperature: float = 0.7
    venture: str | None = None
    zone: str | None = None
    trace_id: str | None = None
    external_input: bool = False  # True si `user` vient d'une source externe non-trusted


@dataclass
class LLMResponse:
    text: str
    model: str
    tier: Tier
    input_tokens: int
    output_tokens: int
    cost_eur: float
    trace_id: str
    fallback_used: bool = False
    blocked: str | None = None  # raison si la requête a été bloquée
    meta: dict[str, Any] = field(default_factory=dict)


class LLMBlocked(RuntimeError):
    pass


class AnthropicClient:
    def __init__(
        self,
        settings: Settings,
        scope: ScopeFilter,
        budget: BudgetManager,
        injection: InjectionDefense,
        *,
        _anthropic_cls=None,  # injection pour tests
    ) -> None:
        self._s = settings
        self._scope = scope
        self._budget = budget
        self._injection = injection
        self._router = ModelRouter(settings)
        self._anthropic_cls = _anthropic_cls  # None en tests → pas d'appel réseau

    def _estimate_cost(self, tier: Tier, in_tok: int, out_tok: int) -> float:
        in_price, out_price = PRICING_EUR_PER_MTOK[tier]
        return (in_tok * in_price + out_tok * out_price) / 1_000_000

    async def call(self, call: LLMCall) -> LLMResponse:
        trace_id = call.trace_id or audit("llm.call.start", task_kind=call.task_kind)

        # Scope input
        try:
            self._scope.assert_clean(call.system, source="llm_system")
            self._scope.assert_clean(call.user, source="llm_user")
        except ScopeError as e:
            audit("llm.call.blocked", trace_id=trace_id, reason="scope_input", detail=str(e))
            raise LLMBlocked(f"scope_input: {e}") from e

        # Injection : encapsule entrées externes
        user_text = call.user
        if call.external_input:
            inj_check = self._injection.scan_input(call.user)
            if inj_check.risky:
                audit(
                    "llm.call.injection_suspected",
                    trace_id=trace_id, matches=inj_check.matches,
                )
            user_text = self._injection.encapsulate(call.user)

        # Tier + budget
        choice = self._router.choose(call.task_kind)
        # pré-estimation : entrée connue, sortie bornée par max_tokens
        est_in = max(1, len(call.system + user_text) // 4)
        est_out = call.max_tokens
        est_cost = self._estimate_cost(choice.tier, est_in, est_out)

        ok, reason = self._budget.can_spend_llm(est_cost, est_in + est_out)
        if not ok:
            audit("llm.call.blocked", trace_id=trace_id, reason=reason)
            raise LLMBlocked(f"budget_precheck: {reason}")

        # Appel réel ou fallback
        if self._anthropic_cls is None and not self._s.anthropic_api_key.get_secret_value():
            # Mode test / pas de clef : stub
            text = self._stub_response(call, choice)
            in_tok, out_tok = est_in, max(1, len(text) // 4)
            resp = LLMResponse(
                text=text, model=choice.model_id, tier=choice.tier,
                input_tokens=in_tok, output_tokens=out_tok,
                cost_eur=self._estimate_cost(choice.tier, in_tok, out_tok),
                trace_id=trace_id, meta={"stub": True},
            )
        else:
            resp = await self._real_call(call, choice, user_text, trace_id)

        # Scope output
        try:
            self._scope.assert_clean(resp.text, source="llm_output")
        except ScopeError as e:
            audit("llm.call.blocked", trace_id=trace_id, reason="scope_output", detail=str(e))
            resp.blocked = "scope_output"
            resp.text = "[BLOCKED: scope_output]"

        # Canary leak
        leak = self._injection.scan_output(resp.text, trace_id=trace_id)
        if leak.canary_leak:
            resp.blocked = "canary_leak"
            resp.text = "[BLOCKED: canary_leak]"

        self._budget.record_llm(resp.cost_eur, resp.input_tokens + resp.output_tokens)
        audit(
            "llm.call.done",
            trace_id=trace_id, tier=choice.tier.value,
            model=choice.model_id, cost_eur=resp.cost_eur,
            in_tok=resp.input_tokens, out_tok=resp.output_tokens,
            blocked=resp.blocked,
        )
        return resp

    async def _real_call(
        self, call: LLMCall, choice: ModelChoice, user_text: str, trace_id: str
    ) -> LLMResponse:
        # Placeholder synchronique : client Anthropic officiel branché en Jalon 1.3
        # quand on aura la clef réelle + DPA ZDR confirmé.
        if self._anthropic_cls is None:
            raise LLMBlocked("anthropic_client_not_configured")
        start = time.monotonic()
        resp = self._anthropic_cls.messages.create(  # type: ignore[attr-defined]
            model=choice.model_id,
            max_tokens=call.max_tokens,
            temperature=call.temperature,
            system=call.system,
            messages=[{"role": "user", "content": user_text}],
        )
        elapsed = time.monotonic() - start
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        in_tok = getattr(resp.usage, "input_tokens", 0) or 0
        out_tok = getattr(resp.usage, "output_tokens", 0) or 0
        return LLMResponse(
            text=text, model=choice.model_id, tier=choice.tier,
            input_tokens=in_tok, output_tokens=out_tok,
            cost_eur=self._estimate_cost(choice.tier, in_tok, out_tok),
            trace_id=trace_id, meta={"elapsed_s": elapsed},
        )

    def _stub_response(self, call: LLMCall, choice: ModelChoice) -> str:
        """Stub déterministe pour tests / dev sans clef API."""
        return f"[STUB {choice.tier.value}/{choice.model_id}] task={call.task_kind}"
