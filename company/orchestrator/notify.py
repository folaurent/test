"""
notify.py — connecteur optionnel Slack / Telegram pour pousser le brief CEO.

Désactivé par défaut. Activé uniquement si les variables d'environnement
sont présentes ET que l'on n'est PAS en dry-run. En dry-run, on journalise
ce qui SERAIT envoyé, sans jamais effectuer d'appel réseau réel.

Variables reconnues :
  SLACK_WEBHOOK_URL          -> envoi Slack via webhook entrant
  TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID -> envoi Telegram

Un envoi vers un canal externe est une action AMBRE (notification opérateur) :
réversible, faible coût, journalisée. Jamais effectuée en dry-run.
"""

from __future__ import annotations

import json
import os
import urllib.request


def _enabled_targets() -> list:
    targets = []
    if os.environ.get("SLACK_WEBHOOK_URL"):
        targets.append("slack")
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        targets.append("telegram")
    return targets


def push_brief(text: str, dry_run: bool = True) -> dict:
    """
    Retourne un dict de statut. N'envoie réellement que si:
      - dry_run is False, ET
      - au moins une cible est configurée par variables d'environnement.
    """
    targets = _enabled_targets()
    if not targets:
        return {"status": "disabled", "reason": "aucun connecteur configuré (env absentes)"}
    if dry_run:
        return {"status": "dry_run", "would_send_to": targets,
                "preview_chars": len(text)}

    results = {}
    if "slack" in targets:
        results["slack"] = _send_slack(text)
    if "telegram" in targets:
        results["telegram"] = _send_telegram(text)
    return {"status": "sent", "results": results}


def send_message(text: str, dry_run: bool = True) -> dict:
    """Notification AMBRE générique vers l'opérateur (Slack/Telegram).

    C'est la « voix » de l'agent : alertes, messages, demandes d'arbitrage.
    Même règles que push_brief (n'envoie que si une cible est configurée ;
    en dry-run, journalise ce qui SERAIT envoyé sans appel réseau)."""
    return push_brief(text, dry_run=dry_run)


def _post_json(url: str, payload: dict) -> int:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
        return resp.status


def _send_slack(text: str) -> str:
    url = os.environ["SLACK_WEBHOOK_URL"]
    # Marge confortable pour ne pas couper une réponse complète de l'agent.
    code = _post_json(url, {"text": text[:8000]})
    return f"http {code}"


def _send_telegram(text: str) -> str:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    code = _post_json(url, {"chat_id": chat_id, "text": text[:4000]})
    return f"http {code}"


# ----------------------------------------------------------------------
#  Lecture Slack (entrant) — pour le dialogue bidirectionnel (--listen).
#  Nécessite un jeton de bot (xoxb-) + l'ID de canal — l'incoming webhook
#  seul ne permet PAS de lire. Dégrade proprement si absents.
# ----------------------------------------------------------------------
def can_read_slack() -> bool:
    return bool(os.environ.get("SLACK_BOT_TOKEN") and os.environ.get("SLACK_CHANNEL_ID"))


def read_slack_messages(oldest_ts: str | None = None, limit: int = 50) -> list:
    """
    Renvoie les messages humains du canal depuis oldest_ts (exclus), du plus
    ancien au plus récent : [{"ts":..., "user":..., "text":...}].
    Filtre les messages de bots (dont les nôtres via webhook).
    """
    if not can_read_slack():
        return []
    token = os.environ["SLACK_BOT_TOKEN"]
    channel = os.environ["SLACK_CHANNEL_ID"]
    url = f"https://slack.com/api/conversations.history?channel={channel}&limit={limit}"
    if oldest_ts:
        url += f"&oldest={oldest_ts}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
        data = json.loads(resp.read().decode("utf-8"))
    if not data.get("ok"):
        return []
    msgs = []
    for m in data.get("messages", []):
        # On ignore les messages de bot / système, on ne garde que les humains.
        if m.get("bot_id") or m.get("subtype") or not m.get("user"):
            continue
        if oldest_ts and m.get("ts") == oldest_ts:
            continue
        msgs.append({"ts": m.get("ts"), "user": m.get("user"), "text": m.get("text", "")})
    msgs.sort(key=lambda x: float(x["ts"]))
    return msgs
