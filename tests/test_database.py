"""Tests unitaires pour la couche de persistance."""

import os
import tempfile

import pytest

from app.models.message import (
    ActionLog,
    Contact,
    ContactCategory,
    GeneratedResponse,
    IncomingMessage,
    ResponseStatus,
)
from app.storage.database import Database


@pytest.fixture
def db():
    """Crée une base de données temporaire pour les tests."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = Database(db_path=path)
    yield database
    os.unlink(path)


class TestDatabase:
    def test_upsert_and_get_contact(self, db):
        contact = Contact(
            name="Alice",
            category=ContactCategory.CLIENT,
            whitelisted=True,
            tone="professional",
        )
        db.upsert_contact(contact)

        result = db.get_contact("Alice")
        assert result is not None
        assert result.name == "Alice"
        assert result.category == ContactCategory.CLIENT
        assert result.whitelisted is True
        assert result.tone == "professional"

    def test_upsert_updates_existing(self, db):
        contact1 = Contact(name="Alice", category=ContactCategory.UNKNOWN)
        db.upsert_contact(contact1)

        contact2 = Contact(name="Alice", category=ContactCategory.CLIENT, whitelisted=True)
        db.upsert_contact(contact2)

        result = db.get_contact("Alice")
        assert result.category == ContactCategory.CLIENT
        assert result.whitelisted is True

    def test_get_nonexistent_contact(self, db):
        result = db.get_contact("Inconnu")
        assert result is None

    def test_save_and_check_message(self, db):
        msg = IncomingMessage(
            contact_name="Alice",
            content="Bonjour",
            message_hash="abc123",
        )
        msg_id = db.save_incoming_message(msg)
        assert msg_id > 0

        assert db.message_exists("abc123") is True
        assert db.message_exists("xyz789") is False

    def test_mark_message_processed(self, db):
        msg = IncomingMessage(
            contact_name="Alice",
            content="Test",
            message_hash="hash1",
        )
        msg_id = db.save_incoming_message(msg)
        db.mark_message_processed(msg_id)

        messages = db.get_recent_messages(10)
        assert len(messages) == 1
        assert messages[0].processed is True

    def test_save_and_get_response(self, db):
        msg = IncomingMessage(
            contact_name="Alice",
            content="Hello",
            message_hash="hash2",
        )
        msg_id = db.save_incoming_message(msg)

        resp = GeneratedResponse(
            incoming_message_id=msg_id,
            contact_name="Alice",
            original_message="Hello",
            response_text="Bonjour !",
            provider="mock",
        )
        resp_id = db.save_response(resp)
        assert resp_id > 0

        assert db.response_exists_for_message(msg_id) is True
        assert db.response_exists_for_message(9999) is False

    def test_update_response_status(self, db):
        msg = IncomingMessage(
            contact_name="Bob",
            content="Test",
            message_hash="hash3",
        )
        msg_id = db.save_incoming_message(msg)

        resp = GeneratedResponse(
            incoming_message_id=msg_id,
            contact_name="Bob",
            original_message="Test",
            response_text="OK",
        )
        resp_id = db.save_response(resp)

        db.update_response_status(resp_id, ResponseStatus.SENT)
        responses = db.get_recent_responses(10)
        assert responses[0].status == ResponseStatus.SENT

    def test_save_and_get_logs(self, db):
        log = ActionLog(action="TEST", details="Test log entry")
        db.save_log(log)

        logs = db.get_recent_logs(10)
        assert len(logs) == 1
        assert logs[0].action == "TEST"

    def test_get_all_contacts(self, db):
        db.upsert_contact(Contact(name="Alice"))
        db.upsert_contact(Contact(name="Bob"))
        db.upsert_contact(Contact(name="Charlie"))

        contacts = db.get_all_contacts()
        assert len(contacts) == 3
        names = [c.name for c in contacts]
        assert "Alice" in names
        assert "Bob" in names
