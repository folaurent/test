"""Budget manager — hard stop par défaut.

Un compteur persistant (ici en mémoire pour Phase 1.1, Redis ensuite) suit :
  - euros LLM / mois
  - euros infra / mois
  - tokens / mois
  - questions Telegram / jour

Dépasser hardstop = tous les appels payants refusent + alerte Telegram.
Le budget infra est à part : limite du Builder pour provisionner.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock

from jarvis.core.config import Settings


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class _Counters:
    llm_eur_month: float = 0.0
    infra_eur_month: float = 0.0
    tokens_month: int = 0
    user_questions_day: int = 0
    reset_month_at: float = 0.0
    reset_day_at: float = 0.0
    lock: Lock = field(default_factory=Lock)


class BudgetManager:
    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._c = _Counters()
        now = time.time()
        self._c.reset_day_at = now + 86400
        self._c.reset_month_at = now + 30 * 86400

    def _rollover(self) -> None:
        now = time.time()
        if now >= self._c.reset_day_at:
            self._c.user_questions_day = 0
            self._c.reset_day_at = now + 86400
        if now >= self._c.reset_month_at:
            self._c.llm_eur_month = 0.0
            self._c.infra_eur_month = 0.0
            self._c.tokens_month = 0
            self._c.reset_month_at = now + 30 * 86400

    def can_spend_llm(self, eur: float, tokens: int) -> tuple[bool, str]:
        with self._c.lock:
            self._rollover()
            if self._c.llm_eur_month + eur > self._s.budget_llm_eur_month:
                return False, "llm_eur_monthly_cap"
            if self._c.tokens_month + tokens > self._s.budget_tokens_month:
                return False, "tokens_monthly_cap"
            return True, "ok"

    def record_llm(self, eur: float, tokens: int) -> None:
        with self._c.lock:
            self._rollover()
            self._c.llm_eur_month += eur
            self._c.tokens_month += tokens
            if self._s.budget_hard_stop and (
                self._c.llm_eur_month > self._s.budget_llm_eur_month
                or self._c.tokens_month > self._s.budget_tokens_month
            ):
                raise BudgetExceeded("llm_hard_stop")

    def can_spend_infra(self, eur: float) -> tuple[bool, str]:
        with self._c.lock:
            self._rollover()
            if self._c.infra_eur_month + eur > self._s.budget_infra_eur_month:
                return False, "infra_eur_monthly_cap"
            return True, "ok"

    def record_infra(self, eur: float) -> None:
        with self._c.lock:
            self._rollover()
            self._c.infra_eur_month += eur
            if self._s.budget_hard_stop and (
                self._c.infra_eur_month > self._s.budget_infra_eur_month
            ):
                raise BudgetExceeded("infra_hard_stop")

    def consume_user_question(self) -> None:
        with self._c.lock:
            self._rollover()
            if self._c.user_questions_day + 1 > self._s.budget_user_questions_per_day:
                raise BudgetExceeded("user_questions_daily_cap")
            self._c.user_questions_day += 1

    def snapshot(self) -> dict[str, float | int]:
        with self._c.lock:
            return {
                "llm_eur_month": self._c.llm_eur_month,
                "infra_eur_month": self._c.infra_eur_month,
                "tokens_month": self._c.tokens_month,
                "user_questions_day": self._c.user_questions_day,
                "llm_cap_eur": self._s.budget_llm_eur_month,
                "infra_cap_eur": self._s.budget_infra_eur_month,
                "tokens_cap": self._s.budget_tokens_month,
                "questions_cap_day": self._s.budget_user_questions_per_day,
            }
