"""
Loader — lecture et parsing des documents produits.
Supporte : JSON (liste d'objets ou {"products": [...]}), CSV, et export Shopify.
Fonctionne en stdlib pure (aucune dépendance requise).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from src.models.product import Product


class LoaderError(Exception):
    """Erreur de lecture/parsing d'un fichier source."""


def _load_json(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        # tolère {"products": [...]} ou un export Shopify {"products": [...]}
        for key in ("products", "items", "data"):
            if key in data and isinstance(data[key], list):
                return data[key]
        raise LoaderError(
            f"JSON objet sans liste 'products'/'items'/'data' dans {path.name}"
        )
    if isinstance(data, list):
        return data
    raise LoaderError(f"Format JSON inattendu dans {path.name}")


def _load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        # détection simple du séparateur , ou ;
        sample = f.read(2048)
        f.seek(0)
        delimiter = ";" if sample.count(";") > sample.count(",") else ","
        reader = csv.DictReader(f, delimiter=delimiter)
        return [dict(row) for row in reader]


def load_products(source: str | Path) -> List[Product]:
    """Charge un fichier produits et retourne une liste de Product.

    Args:
        source: chemin vers un .json ou .csv
    Raises:
        LoaderError: si le fichier est introuvable ou le format non géré.
    """
    path = Path(source)
    if not path.exists():
        raise LoaderError(f"Fichier introuvable : {path}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        rows = _load_json(path)
    elif suffix == ".csv":
        rows = _load_csv(path)
    else:
        raise LoaderError(f"Extension non gérée : {suffix} (attendu .json ou .csv)")

    if not rows:
        raise LoaderError(f"Aucun produit trouvé dans {path.name}")

    products = [Product.from_dict(r) for r in rows]
    return products


def summarize(products: List[Product]) -> dict:
    """Petit récapitulatif utile pour la CLI et les tests."""
    valid = sum(1 for p in products if p.is_valid()[0])
    return {
        "total": len(products),
        "valides": valid,
        "avec_alertes": len(products) - valid,
        "categories": sorted({p.category for p in products if p.category}),
    }
