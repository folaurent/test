import pytest

from jarvis.agents.conversation import (
    ConversationOrchestrator,
    ConvState,
    detect_hot_signal,
    detect_opt_out,
)
from jarvis.core.config import Settings
from jarvis.core.scope import ScopeFilter


@pytest.fixture
def co() -> ConversationOrchestrator:
    return ConversationOrchestrator(ScopeFilter.from_settings(Settings()))


def test_opt_out_detection_multilingual():
    assert detect_opt_out("STOP")
    assert detect_opt_out("unsubscribe please")
    assert detect_opt_out("arrête de m'envoyer ça")
    assert detect_opt_out("pas intéressé merci")
    assert detect_opt_out("no thanks")
    assert not detect_opt_out("ok merci, je regarde")


def test_hot_signal_detection():
    assert detect_hot_signal("On peut faire une démo la semaine pro ?")
    assert detect_hot_signal("Combien ça coûte ?")
    assert not detect_hot_signal("pas dispo cette semaine")


def test_can_send_blocks_after_two_relances(co):
    conv = ConversationOrchestrator.new("prospect_1", "jonction", "FR")
    conv.relances_count = 2
    decision = co.can_send(conv)
    assert not decision.allow
    assert decision.should_break_up


def test_can_send_blocks_on_opt_out(co):
    conv = ConversationOrchestrator.new("prospect_1", "jonction", "FR")
    conv.opt_out = True
    decision = co.can_send(conv)
    assert not decision.allow
    assert decision.reason == "opt_out"


def test_observe_inbound_opt_out_sets_state(co):
    conv = ConversationOrchestrator.new("p", "jonction", "FR")
    co.observe_inbound(conv, "STOP please")
    assert conv.state == ConvState.OPT_OUT
    assert conv.opt_out


def test_observe_inbound_hot_moves_state(co):
    conv = ConversationOrchestrator.new("p", "jonction", "FR")
    co.observe_inbound(conv, "Peut-on faire une démo jeudi ?")
    assert conv.state == ConvState.HOT


def test_prepare_draft_blocks_scope(co):
    conv = ConversationOrchestrator.new("p", "jonction", "FR")
    ok, text, issues = co.prepare_draft(conv, "Hello, je parle de Sika today.")
    assert not ok
    assert "scope_violation" in issues


def test_prepare_draft_blocks_voice_hard(co):
    conv = ConversationOrchestrator.new("p", "jonction", "FR")
    ok, _, issues = co.prepare_draft(conv, "J'espère que vous allez bien. J'écris pour vous proposer notre solution.")
    assert not ok
    assert issues  # au moins une hard issue


def test_break_up_message_format(co):
    conv = ConversationOrchestrator.new("p", "jonction", "FR")
    msg = co.break_up_message(conv, "Jean")
    assert "Jean" in msg
    # Doit passer le lint voice.
    ok, _, _ = co.prepare_draft(conv, msg, first_name_hint="Jean")
    assert ok
