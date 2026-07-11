"""
Orchestrateur "agents / sous-agents".

Idée : le catalogue est traité produit par produit, et pour CHAQUE produit on
enchaîne 3 étapes — dont 2 peuvent être déléguées à des sous-agents LLM :

    [code]      loader         -> Product
    [sous-agent Recherche]     -> offres concurrentes (scraper API ou web-agent)
    [code]      analyzer       -> Price Index + cohérence
    [sous-agent Copywriter]    -> description vendeuse/SEO optimisée
    [code]      reporter       -> rapport Markdown/Excel

En Python "pur", les sous-agents sont des fonctions branchables (API Serper,
API Anthropic). Dans Claude Code, ces étapes peuvent être confiées à de vrais
sous-agents lancés en parallèle (1 par produit) pour accélérer le traitement.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from src.models.product import Product
from src.core.scraper.scraper import search_competitors, CompetitorOffer
from src.core.analyzer.analyzer import analyze_price, check_coherence
from src.core.reporter.reporter import product_markdown


# Signature d'un sous-agent Copywriter (branchable : LLM, template, etc.)
Copywriter = Callable[[Product, list[CompetitorOffer]], str]


def _no_copywriter(product: Product, offers: list[CompetitorOffer]) -> str:
    """Copywriter par défaut : ne fabrique rien (principe : pas d'invention)."""
    return ""


@dataclass
class ProductResult:
    product: Product
    markdown: str
    price_index: Optional[float]
    alerts: list[str]


def analyze_product(product: Product, copywriter: Copywriter = _no_copywriter) -> ProductResult:
    """Pipeline complet pour un produit."""
    offers = search_competitors(product)                       # sous-agent Recherche
    competitor_prices = [o.price for o in offers if o.price]
    price = analyze_price(product, competitor_prices)          # code
    alerts = check_coherence(product, [o.specs for o in offers])  # code
    optimized = copywriter(product, offers)                    # sous-agent Copywriter
    md = product_markdown(product, price, alerts, optimized)
    return ProductResult(product, md, price.price_index, alerts)


def analyze_catalog(products: list[Product],
                    copywriter: Copywriter = _no_copywriter) -> list[ProductResult]:
    """Traite tout le catalogue. (Parallélisable : 1 sous-agent par produit.)"""
    return [analyze_product(p, copywriter) for p in products]
