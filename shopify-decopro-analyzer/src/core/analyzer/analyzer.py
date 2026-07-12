"""
Analyzer — comparaison de prix (Price Index) et cohérence des caractéristiques.
La partie calcul est déterministe ; les données concurrentes viennent du scraper.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Optional

from src.models.product import Product


@dataclass
class PriceAnalysis:
    our_price: Optional[float]
    competitor_prices: list[float]
    market_median: Optional[float]
    price_index: Optional[float]      # 1.0 = au marché ; >1 = plus cher ; <1 = moins cher
    verdict: str


def analyze_price(product: Product, competitor_prices: list[float]) -> PriceAnalysis:
    """Positionne notre prix vs le marché (médiane des concurrents)."""
    comp = [p for p in competitor_prices if isinstance(p, (int, float)) and p > 0]
    if not comp or product.price_ttc is None:
        return PriceAnalysis(product.price_ttc, comp, None, None,
                             "Données insuffisantes")
    med = median(comp)
    index = round(product.price_ttc / med, 2) if med else None
    if index is None:
        verdict = "Données insuffisantes"
    elif index > 1.10:
        verdict = f"Plus cher que le marché (+{(index - 1) * 100:.0f}%)"
    elif index < 0.90:
        verdict = f"Moins cher que le marché ({(index - 1) * 100:.0f}%)"
    else:
        verdict = "Aligné sur le marché"
    return PriceAnalysis(product.price_ttc, comp, med, index, verdict)


def check_coherence(product: Product, competitor_specs: list[dict]) -> list[str]:
    """Repère erreurs/omissions vs ce que montrent les concurrents.

    TODO (à brancher avec le scraper) : comparer dimensions, matériau, finition,
    épaisseur, antidérapance. Pour l'instant, contrôle interne de complétude.
    """
    ok, problems = product.is_valid()
    alerts = list(problems)
    # exemples de règles de complétude « SEO/fiche produit »
    if not product.description_selling:
        alerts.append("description vendeuse absente")
    if product.unit == "m2" and not product.m2_per_box:
        alerts.append("m² par boîte manquant (utile pour le calcul client)")
    if not product.finish:
        alerts.append("finition non renseignée")
    return alerts
