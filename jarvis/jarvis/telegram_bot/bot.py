"""Telegram bot — handlers principaux.

Phase 1.1 : enregistrement des handlers, vérif whitelist, commandes slash
de base. Les commandes complètes (/build, /zones, /campaign, etc.) sont
câblées en Phase 1.2+ une fois les orchestrateurs opérationnels.

Note : le bot ne démarre que si TELEGRAM_BOT_TOKEN est fourni.
"""
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from jarvis.core.config import get_settings
from jarvis.observability.logger import get_logger
from jarvis.telegram_bot.auth import TelegramAuth
from jarvis.telegram_bot.report import MilestoneReport, format_report

logger = get_logger(__name__)


def build_dispatcher() -> tuple[Bot, Dispatcher]:
    settings = get_settings()
    auth = TelegramAuth(settings)
    token = settings.telegram_bot_token.get_secret_value()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN absent — bot non démarré")

    bot = Bot(token=token)
    dp = Dispatcher()

    async def _guard(message: Message) -> bool:
        uid = message.from_user.id if message.from_user else 0
        cid = message.chat.id if message.chat else None
        if not auth.is_authorized(uid, cid):
            logger.warning("telegram.denied", user_id=uid, chat_id=cid)
            return False
        return True

    @dp.message(Command("status"))
    async def on_status(message: Message) -> None:
        if not await _guard(message):
            return
        await message.answer("Jarvis up — Phase 1.1 (socle). Dashboard /dashboard.")

    @dp.message(Command("ping"))
    async def on_ping(message: Message) -> None:
        if not await _guard(message):
            return
        await message.answer("pong")

    @dp.message(Command("scope"))
    async def on_scope(message: Message) -> None:
        if not await _guard(message):
            return
        excluded = ",".join(sorted(get_settings().excluded_ventures))
        await message.answer(f"Périmètre — exclus (verrou dur) : {excluded}")

    return bot, dp


def format_milestone(report: MilestoneReport) -> str:
    """Réexport pratique pour les orchestrateurs."""
    return format_report(report)
