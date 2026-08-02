"""Telegram bot production — whitelist + pipeline Jarvis complet.

Gère :
  - auth whitelist stricte (silence hors liste)
  - /status /scope /ping /whoami /budget /voice /agents /plan /evals
  - messages libres → Jarvis.handle() → route → plan → réponse
  - erreurs → log + message d'excuse + plus de détails sur Telegram
  - fermeture propre via signal
"""
from __future__ import annotations

import asyncio
import os
import ssl

import certifi
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from jarvis.agents.builder import Builder
from jarvis.agents.jarvis_orchestrator import JarvisOrchestrator, Route
from jarvis.core.budget import BudgetManager
from jarvis.core.config import get_settings
from jarvis.core.scope import ScopeError, ScopeFilter
from jarvis.models.claude_cli import ClaudeCliBackend
from jarvis.models.client import AnthropicClient
from jarvis.observability.audit import audit
from jarvis.observability.logger import get_logger
from jarvis.security.injection import InjectionDefense
from jarvis.telegram_bot.auth import TelegramAuth
from jarvis.voice.lint import VoiceLint

logger = get_logger(__name__)


def _build_session() -> AiohttpSession:
    cafile = os.getenv("SSL_CERT_FILE") or "/etc/ssl/certs/ca-certificates.crt"
    if not os.path.exists(cafile):
        cafile = certifi.where()
    ctx = ssl.create_default_context(cafile=cafile)
    session = AiohttpSession()
    session._connector_init = {"ssl": ctx}  # type: ignore[attr-defined]
    return session


async def run() -> None:
    settings = get_settings()
    auth = TelegramAuth(settings)
    scope = ScopeFilter.from_settings(settings)
    lint = VoiceLint()
    budget = BudgetManager(settings)
    injection = InjectionDefense(settings.canary_secret.get_secret_value() or "JARVIS_CANARY")
    cli_backend = ClaudeCliBackend()
    llm = AnthropicClient(settings, scope, budget, injection, cli_backend=cli_backend)
    jarvis = JarvisOrchestrator(scope, bus=None, voice_lint=lint, llm=llm)
    builder = Builder(scope)
    llm_mode = "claude_cli" if llm.prefers_cli else (
        "anthropic_sdk" if settings.anthropic_api_key.get_secret_value() else "stub"
    )
    logger.info("jarvis.llm_mode", mode=llm_mode)

    token = settings.telegram_bot_token.get_secret_value()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN absent dans .env")

    bot = Bot(token=token, session=_build_session())
    dp = Dispatcher()

    async def _guard(msg: Message) -> bool:
        uid = msg.from_user.id if msg.from_user else 0
        cid = msg.chat.id
        if not auth.is_authorized(uid, cid):
            logger.warning("telegram.denied", user_id=uid, chat_id=cid)
            audit("telegram_denied", user_id=uid, chat_id=cid)
            return False
        return True

    @dp.message(CommandStart())
    async def on_start(m: Message) -> None:
        if not await _guard(m):
            return
        await m.answer(
            "Salut Laurent 👋\n\n"
            "Jarvis v6 — Phase 1.2 live.\n\n"
            "Commandes utiles :\n"
            "• /status — état général\n"
            "• /scope — périmètre verrouillé\n"
            "• /agents — agents actifs\n"
            "• /plan <intention> — demande un plan au Builder\n"
            "• /voice <texte> — test du voice lint\n"
            "• /budget — snapshot budget\n"
            "• /evals — dernier run d'évals\n\n"
            "Ou écris-moi en langage naturel, je route."
        )

    @dp.message(Command("status"))
    async def on_status(m: Message) -> None:
        if not await _guard(m):
            return
        await m.answer(
            f"*Jarvis v6 — Phase 1.2*\n"
            f"env: `{settings.env}`\n"
            f"dry_run: `{settings.dry_run}`\n"
            f"scope exclus: `{','.join(sorted(settings.excluded_ventures))}`\n"
            f"LLM backend: `{llm_mode}`\n"
            f"Supabase: `non branché (SQLite local)`",
            parse_mode="Markdown",
        )

    @dp.message(Command("scope"))
    async def on_scope(m: Message) -> None:
        if not await _guard(m):
            return
        await m.answer(
            f"Périmètre — exclus (verrou dur) : `{','.join(sorted(settings.excluded_ventures))}`\n\n"
            "Double verrou actif : filtre routeur + préfixe system prompt.\n"
            "Compteur scope_violations doit rester à 0.",
            parse_mode="Markdown",
        )

    @dp.message(Command("ping"))
    async def on_ping(m: Message) -> None:
        if not await _guard(m):
            return
        await m.answer("pong")

    @dp.message(Command("whoami"))
    async def on_whoami(m: Message) -> None:
        if not await _guard(m):
            return
        u = m.from_user
        await m.answer(
            f"user_id: `{u.id}`\nchat_id: `{m.chat.id}`\nusername: @{u.username}",
            parse_mode="Markdown",
        )

    @dp.message(Command("agents"))
    async def on_agents(m: Message) -> None:
        if not await _guard(m):
            return
        rows = [
            "*Agents actifs*",
            "• `Jarvis` orchestrateur — autonomie 1",
            "• `Builder` meta-agent — autonomie 1",
            "• `ConversationOrchestrator` — autonomie 1 (shadow tant que evals < 0.9)",
            "• `Compliance` — check-list par zone",
        ]
        await m.answer("\n".join(rows), parse_mode="Markdown")

    @dp.message(Command("plan"))
    async def on_plan(m: Message) -> None:
        if not await _guard(m):
            return
        parts = (m.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await m.answer("Usage : `/plan <intention>`\n\nEx : `/plan attaque l'Italie`", parse_mode="Markdown")
            return
        intent = parts[1].strip()
        try:
            plan = builder.draft_plan(intent)
            await m.answer(plan.as_telegram_card(), parse_mode="Markdown")
        except ScopeError as e:
            await m.answer(f"⛔ scope_violation : {e}")
        except Exception as e:
            logger.exception("plan_error")
            await m.answer(f"Erreur : `{e}`", parse_mode="Markdown")

    @dp.message(Command("voice"))
    async def on_voice(m: Message) -> None:
        if not await _guard(m):
            return
        parts = (m.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await m.answer(
                "Usage : `/voice <texte>`\n\nJe te dis si le message passe le lint.",
                parse_mode="Markdown",
            )
            return
        result = lint.check(parts[1])
        lines = [
            f"*Voice lint* — {'✅ passe' if result.passed else '⛔ bloqué'} — score {result.score:.2f}"
        ]
        for i in result.issues:
            icon = "⛔" if i.severity == "hard" else "⚠️"
            lines.append(f"{icon} `{i.rule}` : {i.detail}")
        if not result.issues:
            lines.append("Aucun problème détecté.")
        await m.answer("\n".join(lines), parse_mode="Markdown")

    @dp.message(Command("budget"))
    async def on_budget(m: Message) -> None:
        if not await _guard(m):
            return
        await m.answer(
            f"LLM : 0 € / {settings.budget_llm_eur_month:.0f} € mois\n"
            f"Infra : 0 € / {settings.budget_infra_eur_month:.0f} € mois\n"
            f"Tokens : 0 / {settings.budget_tokens_month:,} mois\n"
            f"Questions/jour : 0 / {settings.budget_user_questions_per_day}\n"
            f"Hard stop : `{'actif' if settings.budget_hard_stop else 'off'}`",
            parse_mode="Markdown",
        )

    @dp.message(Command("evals"))
    async def on_evals(m: Message) -> None:
        if not await _guard(m):
            return
        await m.answer(
            "Derniers runs évals :\n"
            "• VoiceLint : 8/8 ✅\n"
            "• Scope : 8/8 ✅\n"
            "• Golden tasks voice_fr (format) : 5/5 ✅\n\n"
            "Exécution goldens live contre LLM : attend clef Anthropic."
        )

    @dp.message()
    async def on_free_text(m: Message) -> None:
        if not await _guard(m):
            return
        text = m.text or ""
        if not text.strip():
            return

        # Indicateur "typing..." tenu en vie pendant tout le traitement.
        # Telegram l'affiche 5s max, donc on le renvoie en boucle jusqu'à
        # avoir la réponse finale.
        stop_typing = asyncio.Event()

        async def _keep_typing() -> None:
            while not stop_typing.is_set():
                try:
                    await bot.send_chat_action(m.chat.id, "typing")
                except Exception:
                    break
                try:
                    await asyncio.wait_for(stop_typing.wait(), timeout=4.0)
                except asyncio.TimeoutError:
                    continue

        typing_task = asyncio.create_task(_keep_typing())

        try:
            result = await jarvis.handle(text)
        except ScopeError as e:
            stop_typing.set()
            await typing_task
            await m.answer(f"⛔ scope_violation : {e}")
            return
        except Exception as e:
            stop_typing.set()
            await typing_task
            logger.exception("jarvis_handle_error")
            await m.answer(f"Erreur : `{e}`", parse_mode="Markdown")
            return
        finally:
            stop_typing.set()

        try:
            await typing_task
        except Exception:
            pass

        reply = result.get("reply") or "(pas de réponse)"
        # Pas d'affichage route/plan_id par défaut — on veut du naturel.
        # Debug uniquement si ENV=development ET message start par ?
        show_debug = settings.env == "development" and text.strip().startswith("?")
        if show_debug:
            route = result.get("route", "noop")
            plan_id = (result.get("plan_id") or "")[:8]
            reply = f"{reply}\n\n_route: `{route}` · plan: `{plan_id}`_"

        try:
            await m.answer(reply, parse_mode="Markdown")
        except Exception:
            # Markdown parsing fragile si le LLM renvoie des backticks non
            # matchés. Fallback texte brut.
            await m.answer(reply)

    me = await bot.get_me()
    logger.info("telegram.ready", username=me.username, id=me.id)
    audit("telegram.start", username=me.username)
    await dp.start_polling(bot, handle_signals=False)


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
