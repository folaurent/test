"""Telegram auth — whitelist stricte. Tout user/chat hors liste est silencé."""
from __future__ import annotations

from jarvis.core.config import Settings
from jarvis.observability.audit import audit


class TelegramAuth:
    def __init__(self, settings: Settings) -> None:
        self._users = settings.allowed_telegram_user_ids
        self._chats = settings.allowed_telegram_chat_ids

    def is_authorized(self, user_id: int, chat_id: int | None = None) -> bool:
        ok_user = not self._users or user_id in self._users
        ok_chat = not self._chats or (chat_id is not None and chat_id in self._chats)
        return ok_user and ok_chat

    def assert_authorized(self, user_id: int, chat_id: int | None = None) -> None:
        if not self.is_authorized(user_id, chat_id):
            audit(
                "telegram_auth_denied",
                user_id=user_id,
                chat_id=chat_id,
            )
            raise PermissionError(f"unauthorized telegram user={user_id} chat={chat_id}")
