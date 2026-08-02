from jarvis.core.config import Settings
from jarvis.core.model_router import ModelRouter, Tier


def test_router_task_routes_to_haiku():
    r = ModelRouter(Settings())
    choice = r.choose("intent_classification")
    assert choice.tier == Tier.ROUTER


def test_standard_task_routes_to_sonnet():
    r = ModelRouter(Settings())
    choice = r.choose("cold_email_draft")
    assert choice.tier == Tier.STANDARD


def test_critical_task_routes_to_opus():
    r = ModelRouter(Settings())
    choice = r.choose("compliance_review")
    assert choice.tier == Tier.CRITICAL
    choice2 = r.choose("builder_structural_decision")
    assert choice2.tier == Tier.CRITICAL


def test_unknown_task_defaults_to_standard():
    r = ModelRouter(Settings())
    choice = r.choose("weird_new_thing")
    assert choice.tier == Tier.STANDARD


def test_fallback_returns_ollama():
    r = ModelRouter(Settings())
    choice = r.choose("cold_email_draft", fallback=True)
    assert choice.tier == Tier.FALLBACK
    assert "llama" in choice.model_id.lower()
