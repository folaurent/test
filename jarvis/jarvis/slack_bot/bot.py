"""Slack bot production — Socket Mode + whitelist + pipeline Jarvis complet.

Symétrique à telegram_bot/bot.py :
  - auth whitelist stricte (silence hors liste, jamais de leak)
  - événements app_mention (@Jarvis dans un channel) + message.im (DM)
  - free-text → Jarvis.handle() → route → plan → réponse
  - slash commands optionnelles (voir SLASH_COMMANDS ci-dessous) :
      /jarvis-status, /jarvis-ping, /jarvis-scope, /jarvis-voice, /jarvis-plan
    → doivent être déclarées dans le manifest Slack app pour être routées.
  - erreurs → log + message d'excuse en thread

Requires : `slack-bolt` (extras : slack_bolt.adapter.socket_mode.async_handler).
Socket Mode → aucun webhook public à exposer (parfait sandbox + Railway).
"""
from __future__ import annotations

import asyncio
import re
from typing import Any

from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp

from jarvis.agents.builder import Builder
from jarvis.agents.jarvis_orchestrator import JarvisOrchestrator
from jarvis.core.budget import BudgetManager
from jarvis.core.config import get_settings
from jarvis.core.scope import ScopeError, ScopeFilter
from jarvis.models.claude_cli import ClaudeCliBackend
from jarvis.models.client import AnthropicClient
from jarvis.observability.audit import audit
from jarvis.observability.logger import get_logger
from jarvis.security.injection import InjectionDefense
from jarvis.slack_bot.auth import SlackAuth
from jarvis.voice.lint import VoiceLint

logger = get_logger(__name__)

_MENTION_RE = re.compile(r"<@[UW][A-Z0-9]+>")


def _strip_mention(text: str) -> str:
    """Retire le préfixe `<@U0BOT>` d'un app_mention."""
    return _MENTION_RE.sub("", text or "").strip()


async def run() -> None:
    settings = get_settings()
    auth = SlackAuth(settings)
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
    logger.info("jarvis.slack.llm_mode", mode=llm_mode)

    bot_token = settings.slack_bot_token.get_secret_value()
    app_token = settings.slack_app_token.get_secret_value()
    if not bot_token or not app_token:
        raise RuntimeError(
            "SLACK_BOT_TOKEN et SLACK_APP_TOKEN requis dans .env (Socket Mode)."
        )

    app = AsyncApp(token=bot_token)

    async def _guard_event(event: dict[str, Any]) -> bool:
        uid = event.get("user") or ""
        cid = event.get("channel") or ""
        if not auth.is_authorized(uid, cid):
            logger.warning("slack.denied", user_id=uid, channel_id=cid)
            audit("slack_denied", user_id=uid, channel_id=cid)
            return False
        return True

    async def _process_free_text(
        text: str, channel: str, thread_ts: str | None, say
    ) -> None:
        """Pipeline commun aux app_mention + DM."""
        if not text.strip():
            return
        try:
            result = await jarvis.handle(text)
        except ScopeError as e:
            await say(text=f":no_entry: scope_violation : {e}", thread_ts=thread_ts)
            return
        except Exception as e:
            logger.exception("jarvis_handle_error_slack")
            await say(text=f"Erreur : `{e}`", thread_ts=thread_ts)
            return

        reply = result.get("reply") or "(pas de réponse)"
        show_debug = settings.env == "development" and text.strip().startswith("?")
        if show_debug:
            route = result.get("route", "noop")
            plan_id = (result.get("plan_id") or "")[:8]
            reply = f"{reply}\n\n_route: `{route}` · plan: `{plan_id}`_"
        await say(text=reply, thread_ts=thread_ts)

    @app.event("app_mention")
    async def on_mention(event: dict[str, Any], say) -> None:
        if not await _guard_event(event):
            return
        text = _strip_mention(event.get("text", ""))
        thread_ts = event.get("thread_ts") or event.get("ts")
        await _process_free_text(text, event.get("channel", ""), thread_ts, say)

    @app.event("message")
    async def on_message(event: dict[str, Any], say) -> None:
        # Ignore les messages bot / edits / joins — sinon boucle infinie.
        if event.get("subtype") or event.get("bot_id"):
            return
        # Uniquement les DMs (channel_type == "im"). Les mentions channel
        # passent par app_mention.
        if event.get("channel_type") != "im":
            return
        if not await _guard_event(event):
            return
        text = event.get("text", "")
        thread_ts = event.get("thread_ts")  # None pour un top-level DM
        await _process_free_text(text, event.get("channel", ""), thread_ts, say)

    # --- Slash commands (déclarées dans le manifest Slack app) ---

    async def _guard_command(command: dict[str, Any]) -> bool:
        uid = command.get("user_id") or ""
        cid = command.get("channel_id") or ""
        if not auth.is_authorized(uid, cid):
            logger.warning("slack.cmd_denied", user_id=uid, channel_id=cid)
            audit("slack_cmd_denied", user_id=uid, channel_id=cid)
            return False
        return True

    @app.command("/jarvis-ping")
    async def cmd_ping(ack, command, respond) -> None:
        await ack()
        if not await _guard_command(command):
            return
        await respond(text="pong", response_type="ephemeral")

    @app.command("/jarvis-status")
    async def cmd_status(ack, command, respond) -> None:
        await ack()
        if not await _guard_command(command):
            return
        text = (
            f"*Jarvis v6 — Phase 1.2*\n"
            f"env: `{settings.env}` · dry_run: `{settings.dry_run}`\n"
            f"scope exclus: `{','.join(sorted(settings.excluded_ventures))}`\n"
            f"LLM backend: `{llm_mode}`"
        )
        await respond(text=text, response_type="ephemeral")

    @app.command("/jarvis-scope")
    async def cmd_scope(ack, command, respond) -> None:
        await ack()
        if not await _guard_command(command):
            return
        await respond(
            text=(
                f"Périmètre — exclus (verrou dur) : "
                f"`{','.join(sorted(settings.excluded_ventures))}`\n"
                "Double verrou actif : filtre routeur + préfixe system prompt."
            ),
            response_type="ephemeral",
        )

    @app.command("/jarvis-voice")
    async def cmd_voice(ack, command, respond) -> None:
        await ack()
        if not await _guard_command(command):
            return
        raw = (command.get("text") or "").strip()
        if not raw:
            await respond(
                text="Usage : `/jarvis-voice <texte>`", response_type="ephemeral"
            )
            return
        result = lint.check(raw)
        lines = [
            f"*Voice lint* — {':white_check_mark: passe' if result.passed else ':no_entry: bloqué'}"
            f" — score {result.score:.2f}"
        ]
        for i in result.issues:
            icon = ":no_entry:" if i.severity == "hard" else ":warning:"
            lines.append(f"{icon} `{i.rule}` : {i.detail}")
        if not result.issues:
            lines.append("Aucun problème détecté.")
        await respond(text="\n".join(lines), response_type="ephemeral")

    @app.command("/jarvis-plan")
    async def cmd_plan(ack, command, respond) -> None:
        await ack()
        if not await _guard_command(command):
            return
        intent = (command.get("text") or "").strip()
        if not intent:
            await respond(
                text="Usage : `/jarvis-plan <intention>`", response_type="ephemeral"
            )
            return
        try:
            plan = builder.draft_plan(intent)
            await respond(text=plan.as_telegram_card(), response_type="ephemeral")
        except ScopeError as e:
            await respond(text=f":no_entry: scope_violation : {e}", response_type="ephemeral")
        except Exception as e:
            logger.exception("plan_error_slack")
            await respond(text=f"Erreur : `{e}`", response_type="ephemeral")

    handler = AsyncSocketModeHandler(app, app_token)
    logger.info("slack.ready", socket_mode=True)
    audit("slack.start")
    await handler.start_async()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
