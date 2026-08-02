"""Utilitaires de hachage pour la déduplication des messages."""

import hashlib


def compute_message_hash(contact_name: str, content: str) -> str:
    """Génère un hash unique pour un message basé sur le contact et le contenu."""
    raw = f"{contact_name}::{content.strip()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
