import pytest

from jarvis.agents.jarvis_orchestrator import JarvisOrchestrator, Route
from jarvis.core.config import Settings
from jarvis.core.scope import ScopeFilter


@pytest.fixture
def jarvis() -> JarvisOrchestrator:
    return JarvisOrchestrator(ScopeFilter.from_settings(Settings()))


async def test_route_builder_keyword(jarvis):
    r = await jarvis.route("Attaque l'Italie le mois prochain")
    assert r.route == Route.BUILDER


async def test_route_refuses_scope_violation(jarvis):
    r = await jarvis.route("fais un résumé de la stratégie Sika")
    assert r.route == Route.REFUSE


async def test_route_conversation_keyword(jarvis):
    r = await jarvis.route("relance le prospect Dupont")
    assert r.route == Route.CONVERSATION


async def test_plan_builder_route_has_one_step(jarvis):
    intent = await jarvis.route("automatise la relance des factures en retard")
    plan = await jarvis.plan(intent)
    assert len(plan.steps) >= 1


async def test_handle_scope_refusal_returns_polite_message(jarvis):
    out = await jarvis.handle("parle-moi de Parex-Lanko")
    assert out["route"] == "refuse"
    assert "je ne peux pas" in out["reply"].lower()


async def test_handle_default_reply_passes_voice_lint(jarvis):
    out = await jarvis.handle("trouve-moi 50 carreleurs à Lyon")
    # Le default_reply ne doit pas être bloqué par voice lint.
    assert not out["reply"].startswith("[BLOCKED")


async def test_route_meta_on_greeting(jarvis):
    for greeting in [
        "Salut Jarvis",
        "hey jarvis que peux-tu faire pour moi ?",
        "bonjour, qui es-tu ?",
        "aide",
        "comment tu marches ?",
    ]:
        r = await jarvis.route(greeting)
        assert r.route == Route.META, f"failed: {greeting} → {r.route}"


async def test_meta_reply_mentions_capabilities(jarvis):
    out = await jarvis.handle("salut, que peux-tu faire ?")
    assert out["route"] == "meta"
    reply = out["reply"]
    assert "Jarvis" in reply
    assert "/plan" in reply
    assert not reply.startswith("[BLOCKED")


async def test_clarify_not_triggered_by_bare_question(jarvis):
    # "salut que peux tu faire" n'a pas de keyword business → META,
    # pas Research (comme avant le fix).
    r = await jarvis.route("salut jarvis que peux tu faire")
    assert r.route != Route.RESEARCH
