"""
Scraper — recherche concurrentielle (Google Shopping via Serper.dev).

Modes :
  1) API Serper.dev (SERPER_API_KEY) — Google Shopping, rapide et structuré.
  2) Sous-agent "Recherche" (LLM web) — pour extraire des specs sur une fiche
     concurrente quand l'API ne suffit pas (à brancher séparément).

Sans clé API : mode hors-ligne — AUCUN prix inventé (on signale l'absence).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional

from src.models.product import Product

SERPER_SHOPPING_URL = "https://google.serper.dev/shopping"
TIMEOUT = 20


@dataclass
class CompetitorOffer:
    source: str
    title: str
    price: Optional[float]
    url: str = ""
    specs: dict = field(default_factory=dict)


def _query_for(product: Product) -> str:
    parts = [product.brand, product.title, product.dimensions_cm, product.color]
    return " ".join(p for p in parts if p).strip()


def _parse_price(raw) -> Optional[float]:
    """'25,00 €' / '€25.00' / '1 234,50 €' -> float. None si illisible."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw)
    s = re.sub(r"[^\d,.\s]", "", s).strip().replace(" ", "")
    if not s:
        return None
    # format FR "1.234,50" -> "1234.50" ; sinon on retire les virgules de millier
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def search_competitors(product: Product, limit: int = 8) -> list[CompetitorOffer]:
    """Retourne les offres concurrentes pour un produit (Google Shopping)."""
    api_key = os.getenv("SERPER_API_KEY")
    query = _query_for(product)
    if not api_key:
        print(f"  [scraper] Pas de SERPER_API_KEY — recherche ignorée pour: {query!r}")
        return []

    import requests  # import paresseux : le reste du pipeline tourne sans cette dépendance

    country = os.getenv("MARKET_COUNTRY", "fr")
    payload = {"q": query, "gl": country, "hl": country}
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    try:
        resp = requests.post(SERPER_SHOPPING_URL, json=payload, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"  [scraper] Erreur API pour {query!r}: {e}")
        return []

    offers: list[CompetitorOffer] = []
    for item in (data.get("shopping") or [])[:limit]:
        offers.append(CompetitorOffer(
            source=item.get("source", "") or item.get("seller", ""),
            title=item.get("title", ""),
            price=_parse_price(item.get("price")),
            url=item.get("link", ""),
            specs={k: item.get(k) for k in ("delivery", "rating", "ratingCount") if item.get(k)},
        ))
    return offers


def competitor_prices(offers: list[CompetitorOffer]) -> list[float]:
    """Extrait la liste des prix valides (utile pour l'analyzer)."""
    return [o.price for o in offers if isinstance(o.price, (int, float)) and o.price > 0]
