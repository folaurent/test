"""
llm.py — pont vers le LLM (Claude API) pour la cognition des agents.

Principe de conception (cohérent avec les garde-fous) :
  - Un appel LLM est une action AMBRE : externe et à faible coût.
  - Il n'est exécuté pour de vrai QUE si : (1) on n'est pas en dry-run,
    (2) le SDK `anthropic` est installé, (3) ANTHROPIC_API_KEY est présent,
    (4) le budget le permet.
  - Sinon, `complete()` renvoie None et l'appelant retombe sur sa logique
    déterministe (stub). Le dry-run reste donc sans effet de bord externe.

Le coût estimé de chaque appel est renvoyé pour que la boucle l'impute au
budget (cycle + global) via guardrails.

Modèle par défaut : claude-opus-4-8 (le plus capable), surchargeable via
la variable d'environnement COMPANY_LLM_MODEL.
"""

from __future__ import annotations

import os

DEFAULT_MODEL = os.environ.get("COMPANY_LLM_MODEL", "claude-opus-4-8")

# Tarifs indicatifs $/million de tokens (entrée, sortie) — pour estimer le coût.
PRICING = {
    "claude-opus-4-8": (5.0, 25.0),
    "claude-opus-4-7": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-fable-5": (10.0, 50.0),
}


def available() -> bool:
    """Vrai si un appel LLM réel est possible (SDK + clé présents)."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except Exception:
        return False
    return True


def status() -> str:
    if available():
        return f"live-capable (model={DEFAULT_MODEL})"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "key set but SDK `anthropic` missing"
    return "stub (no ANTHROPIC_API_KEY)"


def estimate_cost(in_tokens: int, out_tokens: int, model: str = DEFAULT_MODEL) -> float:
    pin, pout = PRICING.get(model, PRICING[DEFAULT_MODEL])
    return (in_tokens / 1_000_000) * pin + (out_tokens / 1_000_000) * pout


def complete(system: str, user: str, *, dry_run: bool = True,
             model: str = DEFAULT_MODEL, max_tokens: int = 1024,
             effort: str = "high") -> dict | None:
    """
    Effectue un appel LLM réel et renvoie
        {"text": str, "in_tokens": int, "out_tokens": int, "cost": float, "model": str}
    Renvoie None si l'appel ne doit pas / ne peut pas être effectué
    (dry-run, SDK absent, clé absente) — l'appelant doit alors utiliser sa
    logique déterministe de repli.
    """
    if dry_run or not available():
        return None

    import anthropic

    client = anthropic.Anthropic()  # lit ANTHROPIC_API_KEY depuis l'environnement
    # Adaptive thinking + effort (recommandé sur Opus 4.6+).
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    in_tok = resp.usage.input_tokens
    out_tok = resp.usage.output_tokens
    return {
        "text": text,
        "in_tokens": in_tok,
        "out_tokens": out_tok,
        "cost": round(estimate_cost(in_tok, out_tok, model), 6),
        "model": model,
    }
