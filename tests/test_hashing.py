"""Tests unitaires pour le module de hachage."""

from app.utils.hashing import compute_message_hash


class TestHashing:
    def test_same_input_same_hash(self):
        h1 = compute_message_hash("Alice", "Bonjour")
        h2 = compute_message_hash("Alice", "Bonjour")
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = compute_message_hash("Alice", "Bonjour")
        h2 = compute_message_hash("Alice", "Au revoir")
        assert h1 != h2

    def test_different_contact_different_hash(self):
        h1 = compute_message_hash("Alice", "Bonjour")
        h2 = compute_message_hash("Bob", "Bonjour")
        assert h1 != h2

    def test_strips_whitespace(self):
        h1 = compute_message_hash("Alice", "Bonjour")
        h2 = compute_message_hash("Alice", "  Bonjour  ")
        assert h1 == h2

    def test_hash_is_hex_string(self):
        h = compute_message_hash("Alice", "Hello")
        assert all(c in "0123456789abcdef" for c in h)
        assert len(h) == 64  # SHA-256
