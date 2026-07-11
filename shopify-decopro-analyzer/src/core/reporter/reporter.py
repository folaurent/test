"""
Reporter — génère le rapport d'analyse par produit (Markdown, puis Excel/CSV).
Format de sortie conforme au cahier des charges (5 sections).
"""
from __future__ import annotations

from pathlib import Path

from src.models.product import Product
from src.core.analyzer.analyzer import PriceAnalysis


def product_markdown(product: Product, price: PriceAnalysis, alerts: list[str],
                     optimized_selling: str = "") -> str:
    """Rapport Markdown structuré pour UN produit (les 5 sections demandées)."""
    comp_line = (f"{price.market_median:.2f} € (médiane de {len(price.competitor_prices)} offres)"
                 if price.market_median else "aucune donnée concurrent")
    alerts_md = "\n".join(f"  - ⚠️ {a}" for a in alerts) or "  - ✅ aucune alerte"
    return f"""## {product.title}
`{product.sku}` · {product.category} · {product.brand}

**1. Description rapide**
{product.description_short or "_(à rédiger)_"}

**2. Description vendeuse — actuelle vs optimisée**
- Actuelle : {product.description_selling or "_(absente)_"}
- Optimisée : {optimized_selling or "_(sera générée par le sous-agent Copywriter)_"}

**3. Caractéristiques — cohérence**
| Champ | Notre site | Alertes |
|---|---|---|
| Dimensions | {product.dimensions_cm or "—"} | |
| Matériau | {product.material or "—"} | |
| Finition | {product.finish or "—"} | |
| Couleur | {product.color or "—"} | |

Alertes de cohérence :
{alerts_md}

**4. Analyse de prix (positionnement marché)**
- Notre prix : {product.price_label}
- Marché : {comp_line}
- Price Index : {price.price_index if price.price_index is not None else "—"} → **{price.verdict}**

**5. Description marketing alternative (grand public)**
{optimized_selling or "_(à générer)_"}

---
"""


def write_report(products_md: list[str], out_dir: str | Path = "data/output",
                 filename: str = "rapport_analyse.md") -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / filename
    header = "# Rapport d'analyse concurrentielle — Deco & Pro\n\n"
    path.write_text(header + "\n".join(products_md), encoding="utf-8")
    return path
