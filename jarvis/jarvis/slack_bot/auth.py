"""Slack auth — whitelist stricte user_id + channel_id. Symétrique à TelegramAuth."""
from __future__ import annotations

from jarvis.core.config import Settings
from jarvis.observability.audit import audit


class SlackAuth:
    def __init__(self, settings: Settings) -> None:
        self._users = settings.allowed_slack_user_ids
        self._channels = settings.allowed_slack_channel_ids

    def is_authorized(self, user_id: str, channel_id: str | None = None) -> bool:
        ok_user = not self._users or user_id in self._users
        ok_channel = not self._channels or (
            channel_id is not None and channel_id in self._channels
        )
        return ok_user and ok_channel

    def assert_authorized(self, user_id: str, channel_id: str | None = None) -> None:
        if not self.is_authorized(user_id, channel_id):
            audit("slack_auth_denied", user_id=user_id, channel_id=channel_id)
            raise PermissionError(f"unauthorized slack user={user_id} channel={channel_id}")
