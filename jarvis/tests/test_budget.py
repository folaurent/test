import pytest

from jarvis.core.budget import BudgetExceeded, BudgetManager
from jarvis.core.config import Settings


def _s(**overrides):
    base = {
        "budget_llm_eur_month": 10.0,
        "budget_infra_eur_month": 5.0,
        "budget_tokens_month": 1000,
        "budget_user_questions_per_day": 3,
        "budget_hard_stop": True,
    }
    base.update(overrides)
    return Settings(**base)


def test_can_spend_before_cap():
    b = BudgetManager(_s())
    ok, _ = b.can_spend_llm(eur=1.0, tokens=100)
    assert ok


def test_record_llm_accumulates():
    b = BudgetManager(_s())
    b.record_llm(eur=2.0, tokens=100)
    snap = b.snapshot()
    assert snap["llm_eur_month"] == 2.0


def test_hard_stop_trips_over_cap():
    b = BudgetManager(_s())
    with pytest.raises(BudgetExceeded):
        b.record_llm(eur=20.0, tokens=10)


def test_user_questions_daily_cap():
    b = BudgetManager(_s())
    b.consume_user_question()
    b.consume_user_question()
    b.consume_user_question()
    with pytest.raises(BudgetExceeded):
        b.consume_user_question()


def test_infra_cap():
    b = BudgetManager(_s())
    ok, _ = b.can_spend_infra(3.0)
    assert ok
    b.record_infra(3.0)
    ok, reason = b.can_spend_infra(3.0)
    assert not ok
    assert reason == "infra_eur_monthly_cap"
