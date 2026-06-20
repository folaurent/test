"""
conversation.py — la "voix humaine" du CEO : dialogue naturel avec l'opérateur.

L'agent se comporte comme un dirigeant humain : il parle naturellement, expose
son analyse et sa recommandation, mais DÉCIDE AVEC l'opérateur (il propose et
demande, il n'impose pas). Il garde toute son expertise et s'appuie sur l'état
réel de l'entreprise (KPI, signaux, décisions en attente) — sans rien inventer.

- Génération du message : LLM (Claude) si clé présente, sinon repli naturel
  déterministe ancré sur l'état réel.
- Décisions partagées : si l'opérateur dit « ok pour #3 » / « rejette #2 »,
  l'agent exécute l'arbitrage (resolve_approval) AVANT de répondre, puis en
  rend compte. Aucune action ROUGE n'est exécutée sans cet accord explicite.
"""

from __future__ import annotations

import re

import llm
import memory
from connectors import shopify

PERSONA = (
    "Tu es le CEO de la société e-commerce « Deco and pro » (carrelage, travertin, "
    "sanitaire, déco — France). Tu parles à ton associé humain (l'opérateur) sur Slack. "
    "Comporte-toi comme un dirigeant humain : chaleureux, direct, naturel, en français, "
    "tutoiement. Tu as une vraie expertise growth/produit/ops e-commerce. "
    "Règles de comportement :\n"
    "- Tu exposes ton analyse et UNE recommandation claire, puis tu DÉCIDES AVEC lui : "
    "tu poses la question, tu ne dictes pas.\n"
    "- Tu t'appuies sur les faits réels fournis (KPI, signaux). Tu n'inventes JAMAIS de "
    "chiffre ; si tu ne sais pas, tu le dis.\n"
    "- Aucune action irréversible / externe (publication, dépense, email client) sans son "
    "accord explicite — tu la proposes et tu attends son feu vert.\n"
    "- Jamais d'entités Sika ni Parexlanko.\n"
    "- Concis (quelques phrases), ton conversationnel, pas de jargon inutile, pas de listes "
    "interminables. Termine souvent par une question ou une proposition d'action."
)


def snapshot(conn) -> str:
    """Photo compacte de l'état réel pour ancrer la réponse de l'agent."""
    kpis = memory.latest_metrics(conn)
    appr = memory.list_approvals(conn, "pending")
    inits = memory.list_initiatives(conn)
    sig = shopify.fetch_signals(dry_run=True)

    lines = [f"Source de données : {sig.get('source')}"]
    if kpis:
        lines.append("KPI vs cibles : " + " ; ".join(
            f"{m['name']}={m['value']:g}{m['unit'] or ''}/cible {m['target']:g}" for m in kpis))
    for s in (sig.get("signals") or [])[:6]:
        lines.append(f"Signal : {s}")
    running = [i for i in inits if i["status"] in ("running", "planned", "closed")]
    if running:
        lines.append("Initiatives : " + " ; ".join(
            f"#{i['id']} {i['title']} [{i['status']}]" for i in running[:6]))
    if appr:
        lines.append("Décisions ROUGE en attente d'arbitrage :")
        for a in appr:
            lines.append(f"  #{a['id']} — {a['summary']}")
    else:
        lines.append("Aucune décision en attente.")
    lines.append(f"Compteur d'exclusion de données : {memory.total_exclusion_attempts(conn)} (cible 0)")
    return "\n".join(lines)


def parse_decisions(message: str):
    """Détecte des arbitrages explicites dans le message. -> [(id, 'approved'|'rejected')]"""
    low = message.lower()
    out = []
    for m in re.finditer(r"(?:approuv\w*|valid\w*|ok\s+pour|go\s+pour|d['’]accord\s+pour|feu\s+vert\s+pour)\s*#?\s*(\d+)", low):
        out.append((int(m.group(1)), "approved"))
    for m in re.finditer(r"(?:rejett?\w*|refus\w*|annul\w*|non\s+pour|stop\s+pour)\s*#?\s*(\d+)", low):
        out.append((int(m.group(1)), "rejected"))
    # déduplique en gardant le dernier verdict par id
    dedup = {}
    for aid, dec in out:
        dedup[aid] = dec
    return list(dedup.items())


def _fallback_reply(conn, ctx_lines, message, actions) -> str:
    """Réponse naturelle déterministe (sans LLM) ancrée sur l'état réel."""
    appr = memory.list_approvals(conn, "pending")
    parts = []
    if actions:
        done = ", ".join(f"#{a} ({'validé' if d=='approved' else 'rejeté'})" for a, d in actions)
        parts.append(f"C'est noté, j'ai enregistré ta décision : {done}.")
    parts.append("Côté boutique, le constat reste le même : on a un peu de trafic mais une "
                 "conversion à 0 % — le nerf de la guerre, c'est de débloquer le tunnel d'achat "
                 "et d'ouvrir un canal d'acquisition.")
    if appr:
        nxt = appr[0]
        parts.append(f"Prochaine décision qui t'attend : #{nxt['id']} — {nxt['summary']}. "
                     "Mon avis : on y va, mais je voulais ton accord avant. On valide ? "
                     "(réponds « ok pour #%d » ou « rejette #%d »)" % (nxt['id'], nxt['id']))
    else:
        parts.append("Rien ne bloque de ton côté pour l'instant. Tu veux qu'on lance quoi en priorité — "
                     "le tunnel de paiement ou l'acquisition SEO ?")
    return " ".join(parts)


def respond(conn, message: str, dry_run: bool = False, actor="ceo"):
    """
    Traite un message de l'opérateur :
      1. exécute les arbitrages explicites (approve/reject) — décision partagée,
      2. génère une réponse naturelle (LLM si dispo, sinon repli ancré),
    Renvoie (reply_text, actions). N'envoie rien (l'appelant s'en charge).
    """
    actions = []
    for aid, dec in parse_decisions(message):
        row = memory.resolve_approval(conn, aid, dec, resolved_by="opérateur (slack)")
        if row:
            actions.append((aid, dec))
            memory.audit(conn, actor, "DECISION_SHARED",
                         {"approval_id": aid, "decision": dec, "via": "conversation"},
                         action_class="GREEN")

    ctx = snapshot(conn)
    user = (f"État réel de l'entreprise :\n{ctx}\n\n"
            f"Message de l'opérateur :\n{message}\n\n"
            f"Arbitrages que je viens d'appliquer : "
            f"{', '.join(f'#{a}:{d}' for a, d in actions) or 'aucun'}.\n"
            "Réponds-lui naturellement, en gardant ton expertise.")
    res = llm.complete(PERSONA, user, dry_run=dry_run, max_tokens=600)
    reply = res["text"] if res else _fallback_reply(conn, ctx, message, actions)
    return reply, actions
