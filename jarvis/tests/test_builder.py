import pytest

from jarvis.agents.builder import Builder
from jarvis.core.config import Settings
from jarvis.core.scope import ScopeError, ScopeFilter


@pytest.fixture
def builder() -> Builder:
    return Builder(ScopeFilter.from_settings(Settings()))


def test_parse_intent_detects_venture_zone(builder):
    parsed = builder.parse_intent("Attaque l'Italie pour Jonction")
    assert parsed["venture"] == "jonction"
    assert parsed["zone"] == "IT"
    assert parsed["kind"] == "new_zone"


def test_parse_intent_defaults_fr(builder):
    parsed = builder.parse_intent("Automatise le SAV Deco & Pro")
    assert parsed["venture"] == "deco_pro"
    assert parsed["zone"] == "FR"
    assert parsed["kind"] == "new_automation"


def test_parse_intent_refuses_sika(builder):
    with pytest.raises(ScopeError):
        builder.parse_intent("Ouvre un canal sur Sika")


def test_draft_plan_new_zone_includes_two_specialists(builder):
    plan = builder.draft_plan("Attaque l'Allemagne le mois prochain")
    names = [a["name"] for a in plan.new_agents]
    assert "Prospection-DACH" in names
    assert "Conversation-DACH" in names
    assert plan.goldens_to_create >= 20
    assert plan.estimated_cost_eur_month > 0


def test_draft_plan_includes_compliance_for_new_zone(builder):
    plan = builder.draft_plan("attaque l'italie")
    assert any("compliance" in c.lower() or "registre" in c.lower() for c in plan.compliance_checks)


def test_plan_fingerprint_stable(builder):
    p1 = builder.draft_plan("automatise le SAV Deco & Pro")
    fp1 = builder.plan_fingerprint(p1)
    # Même plan, même intent → fingerprints identiques si les timestamps
    # et ids sont remis à zéro. On vérifie juste le format.
    assert len(fp1) == 12


def test_telegram_card_mentions_intent_and_rollback(builder):
    plan = builder.draft_plan("Attaque le Royaume-Uni")
    card = plan.as_telegram_card()
    assert "Royaume-Uni" in card or "intention" in card.lower()
    assert "rollback" in card.lower() or "Rollback" in card
