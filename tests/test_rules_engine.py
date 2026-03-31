"""Tests unitaires pour le moteur de règles."""

import pytest

from app.models.message import Contact, ContactCategory, ResponseMode
from app.services.rules_engine import MessagePriority, RulesEngine


@pytest.fixture
def engine():
    return RulesEngine(
        whitelist=[],
        blacklist=["spammer"],
        default_mode="draft_only",
        default_tone="neutral",
        user_name="moi",
    )


@pytest.fixture
def client_contact():
    return Contact(
        name="Claire Client",
        category=ContactCategory.CLIENT,
        whitelisted=True,
        auto_reply_enabled=False,
        tone="professional",
    )


@pytest.fixture
def friend_contact():
    return Contact(
        name="David Ami",
        category=ContactCategory.FRIEND,
        whitelisted=True,
        auto_reply_enabled=True,
        tone="friendly",
    )


class TestRulesEngine:
    def test_anti_loop_own_messages(self, engine):
        """Ne jamais traiter ses propres messages."""
        result = engine.evaluate("Moi", "Bonjour", None)
        assert not result.should_process
        assert "anti-boucle" in result.reason.lower()

    def test_blacklisted_contact(self, engine):
        """Ignorer les contacts blacklistés."""
        result = engine.evaluate("Spammer", "Achète mes trucs", None)
        assert not result.should_process
        assert "blacklist" in result.reason.lower()

    def test_blacklisted_via_contact_object(self, engine):
        contact = Contact(name="Nuisible", blacklisted=True)
        result = engine.evaluate("Nuisible", "Hello", contact)
        assert not result.should_process

    def test_empty_message(self, engine):
        result = engine.evaluate("Alice", "", None)
        assert not result.should_process

    def test_short_message(self, engine):
        result = engine.evaluate("Alice", "a", None)
        assert not result.should_process

    def test_normal_message_accepted(self, engine):
        result = engine.evaluate("Alice", "Bonjour, comment vas-tu ?", None)
        assert result.should_process

    def test_whitelist_filtering(self):
        engine = RulesEngine(whitelist=["alice"], blacklist=[])
        result = engine.evaluate("Bob", "Salut !", None)
        assert not result.should_process
        assert "non whitelisté" in result.reason.lower()

        result = engine.evaluate("Alice", "Salut !", None)
        assert result.should_process

    def test_urgent_priority(self, engine):
        result = engine.evaluate("Alice", "URGENT: besoin d'aide immédiatement", None)
        assert result.priority == MessagePriority.URGENT
        assert result.alert is True

    def test_question_priority(self, engine):
        result = engine.evaluate("Alice", "Comment faire pour configurer le serveur ?", None)
        assert result.priority == MessagePriority.HIGH

    def test_client_tone(self, engine, client_contact):
        result = engine.evaluate("Claire Client", "Besoin d'un devis", client_contact)
        assert result.tone == "professional"

    def test_friend_tone(self, engine, friend_contact):
        result = engine.evaluate("David Ami", "On sort ce soir ?", friend_contact)
        assert result.tone == "friendly"

    def test_auto_reply_mode(self, engine, friend_contact):
        result = engine.evaluate("David Ami", "Hello !", friend_contact)
        assert result.response_mode == ResponseMode.AUTO_REPLY

    def test_default_draft_mode(self, engine, client_contact):
        result = engine.evaluate("Claire Client", "Bonjour", client_contact)
        assert result.response_mode == ResponseMode.DRAFT_ONLY

    def test_template_mode(self, engine):
        engine.set_template_mode("absence")
        result = engine.evaluate("Alice", "Es-tu là ?", None)
        assert result.use_template is True
        assert result.template_response is not None
        assert "indisponible" in result.template_response.lower()

    def test_template_mode_disable(self, engine):
        engine.set_template_mode("absence")
        engine.set_template_mode(None)
        result = engine.evaluate("Alice", "Es-tu là ?", None)
        assert result.use_template is False

    def test_update_lists(self, engine):
        engine.update_lists(["alice", "bob"], ["spammer2"])
        assert "alice" in engine.whitelist
        assert "spammer2" in engine.blacklist
