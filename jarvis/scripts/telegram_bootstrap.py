"""Bootstrap Telegram — mode découverte.

Démarre le bot avec la whitelist vide (mode bootstrap). Chaque message reçu :
  - log user_id + chat_id + username
  - accuse réception sans rien faire d'engageant
Une fois que Laurent a envoyé /start, on lit le log pour récupérer son ID et
on met à jour .env avec TELEGRAM_ALLOWED_USER_IDS=<id>, puis on redémarre en
mode "whitelist strict".

Lance :
  TELEGRAM_BOT_TOKEN=xxx python scripts/telegram_bootstrap.py
"""
import asyncio
import json
import os
import ssl
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import certifi
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiohttp import TCPConnector


def _build_session() -> AiohttpSession:
    """Session aiohttp qui fait confiance au CA bundle système.

    Le sandbox interpose une CA (egress TLS inspection). Par défaut aiohttp
    n'utilise que certifi → échec. On reconstruit le contexte avec
    /etc/ssl/certs/ca-certificates.crt qui contient la CA d'Anthropic.
    """
    cafile = os.getenv("SSL_CERT_FILE") or "/etc/ssl/certs/ca-certificates.crt"
    if not os.path.exists(cafile):
        cafile = certifi.where()
    ctx = ssl.create_default_context(cafile=cafile)
    connector_factory = lambda: TCPConnector(ssl=ctx)  # noqa: E731
    session = AiohttpSession()
    # Patch : aiogram v3 crée le connector à la volée via _connector_init.
    session._connector_init = {"ssl": ctx}  # type: ignore[attr-defined]
    return session

from jarvis.core.scope import ScopeFilter
from jarvis.core.config import Settings
from jarvis.observability.logger import configure_logging, get_logger
from jarvis.voice.dna import voice_system_prompt

BOOTSTRAP_LOG = Path("data/telegram_bootstrap.jsonl")
BOOTSTRAP_LOG.parent.mkdir(parents=True, exist_ok=True)

logger = get_logger("telegram_bootstrap")


def record(event: str, **fields):
    line = {"ts": time.time(), "event": event, **fields}
    BOOTSTRAP_LOG.open("a", encoding="utf-8").write(
        json.dumps(line, ensure_ascii=False, default=str) + "\n"
    )
    logger.info("telegram." + event, **fields)


async def main():
    configure_logging("INFO")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN manquant", file=sys.stderr)
        sys.exit(1)

    # Scope filter appliqué même en mode bootstrap.
    ScopeFilter.from_settings(Settings())

    bot = Bot(token=token, session=_build_session())
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def on_start(msg: Message):
        u = msg.from_user
        record(
            "start",
            user_id=u.id if u else None,
            username=u.username if u else None,
            first_name=u.first_name if u else None,
            chat_id=msg.chat.id,
            chat_type=msg.chat.type,
        )
        await msg.answer(
            "Salut. Je suis l'assistant de Laurent.\n\n"
            "Pour l'instant je tourne en mode bootstrap : je capture ton identifiant "
            "pour la whitelist, mais je ne fais encore rien d'autre.\n\n"
            f"Ton user_id : `{u.id if u else '?'}`\n"
            f"Chat id : `{msg.chat.id}`\n\n"
            "Laurent va utiliser ça pour me whitelister proprement, puis je serai "
            "fully operational."
        )

    @dp.message(Command("whoami"))
    async def on_whoami(msg: Message):
        u = msg.from_user
        record("whoami", user_id=u.id if u else None, chat_id=msg.chat.id)
        await msg.answer(f"user_id=`{u.id}` chat_id=`{msg.chat.id}`")

    @dp.message(Command("ping"))
    async def on_ping(msg: Message):
        record("ping", user_id=msg.from_user.id if msg.from_user else None)
        await msg.answer("pong — bootstrap mode")

    @dp.message(Command("scope"))
    async def on_scope(msg: Message):
        s = Settings()
        record("scope_query", user_id=msg.from_user.id if msg.from_user else None)
        await msg.answer(
            "Périmètre exclus (verrou dur) : " + ", ".join(sorted(s.excluded_ventures))
        )

    @dp.message()
    async def on_any(msg: Message):
        u = msg.from_user
        record(
            "message",
            user_id=u.id if u else None,
            username=u.username if u else None,
            chat_id=msg.chat.id,
            text=(msg.text or "")[:200],
        )
        await msg.answer(
            "Bien reçu 👀\n\n"
            "Je suis encore en bootstrap. Envoie /start pour t'identifier, "
            "ensuite Laurent m'active."
        )

    logger.info("telegram.bootstrap.start")
    me = await bot.get_me()
    logger.info("telegram.bot.identity", username=me.username, id=me.id)
    await dp.start_polling(bot, handle_signals=False)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
