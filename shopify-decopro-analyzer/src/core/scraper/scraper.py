"""
Scraper — recherche concurrentielle (Google Shopping / sites concurrents).

Deux modes prévus :
  1) API de recherche (Serper.dev ou SerpAPI)  -> déterministe, rapide.
  2) Sous-agent "Recherche" (LLM avec accès web) -> pour les cas où l'API
     ne suffit pas (extraction de specs sur une fiche produit concurrente).

Ce module expose une interface stable ; l'implémentation réseau est à activer
avec une clé API (voir .env). En l'absence de clé, `search_competitors`
retourne une réponse simulée pour permettre de tester le pipeline.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from src.models.product import Product


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


def search_competitors(product: Product, limit: int = 5) -> list[CompetitorOffer]:
    """Recherche les offres concurrentes pour un produit.

    Si SERPER_API_KEY / SERPAPI_KEY est présent, interroge l'API.
    Sinon, renvoie une liste vide + un avertissement (mode hors-ligne).
    """
    api_key = os.getenv("SERPER_API_KEY") or os.getenv("SERPAPI_KEY")
    query = _query_for(product)
    if not api_key:
        # Mode hors-ligne : on ne fabrique pas de faux prix (principe : pas d'invention).
        print(f"  [scraper] Pas de clé API — recherche ignorée pour: {query!r}")
        return []
    # TODO: implémenter l'appel Serper/SerpAPI ici (requests.post ...).
    raise NotImplementedError(
        "Brancher l'appel Serper/SerpAPI. Query prête = " + repr(query)
    )
