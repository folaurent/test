"""SlackAuth — whitelist stricte user_id + channel_id."""
import pytest

from jarvis.core.config import Settings
from jarvis.slack_bot.auth import SlackAuth


def _s(users: str = "", channels: str = "") -> Settings:
    return Settings(
        slack_allowed_user_ids=users,
        slack_allowed_channel_ids=channels,
    )


def test_open_when_no_whitelist_configured():
    # Comportement identique à TelegramAuth : listes vides = tout accepté
    # (utile en dev local, à durcir en prod via env var).
    auth = SlackAuth(_s())
    assert auth.is_authorized("U123", "C123") is True


def test_user_whitelist_blocks_outsiders():
    auth = SlackAuth(_s(users="U_LAURENT"))
    assert auth.is_authorized("U_LAURENT", "C1") is True
    assert auth.is_authorized("U_HACKER", "C1") is False


def test_channel_whitelist_blocks_outsiders():
    auth = SlackAuth(_s(channels="C_JARVIS"))
    assert auth.is_authorized("U_LAURENT", "C_JARVIS") is True
    assert auth.is_authorized("U_LAURENT", "C_RANDOM") is False


def test_both_whitelists_are_ANDed():
    auth = SlackAuth(_s(users="U_LAURENT", channels="C_JARVIS"))
    assert auth.is_authorized("U_LAURENT", "C_JARVIS") is True
    assert auth.is_authorized("U_LAURENT", "C_OTHER") is False
    assert auth.is_authorized("U_HACKER", "C_JARVIS") is False


def test_assert_authorized_raises_on_deny():
    auth = SlackAuth(_s(users="U_LAURENT"))
    with pytest.raises(PermissionError):
        auth.assert_authorized("U_HACKER", "C1")


def test_channel_whitelist_needs_channel_id():
    auth = SlackAuth(_s(channels="C_JARVIS"))
    # channel_id=None avec whitelist channels active → refusé.
    assert auth.is_authorized("U_LAURENT", None) is False


def test_csv_parsing_trims_spaces():
    auth = SlackAuth(_s(users="U1, U2 ,U3"))
    for uid in ("U1", "U2", "U3"):
        assert auth.is_authorized(uid, "C1") is True
    assert auth.is_authorized("U4", "C1") is False
