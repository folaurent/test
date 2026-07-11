"""Modèle de données Produit — Shopify-DecoPro-Analyzer."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Product:
    """Représente un produit du catalogue Deco & Pro."""
    id: str
    title: str
    sku: str = ""
    category: str = ""
    brand: str = ""
    material: str = ""
    dimensions_cm: str = ""
    thickness_mm: Optional[float] = None
    color: str = ""
    finish: str = ""
    unit: str = "piece"                 # "m2" ou "piece"
    price_ttc: Optional[float] = None
    m2_per_box: Optional[float] = None
    stock: Optional[int] = None
    url: str = ""
    description_short: str = ""
    description_selling: str = ""
    # Champs bruts non modélisés (on ne perd aucune donnée source)
    extra: dict = field(default_factory=dict)

    # -- Fabrique tolérante : accepte des clés inconnues sans planter --------
    @classmethod
    def from_dict(cls, data: dict) -> "Product":
        known = {f for f in cls.__dataclass_fields__ if f != "extra"}
        base = {k: v for k, v in data.items() if k in known}
        extra = {k: v for k, v in data.items() if k not in known}
        # id de secours si absent
        if not base.get("id"):
            base["id"] = base.get("sku") or base.get("title", "sans-id")
        if not base.get("title"):
            base["title"] = base.get("sku") or base["id"]
        return cls(**base, extra=extra)

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def price_label(self) -> str:
        if self.price_ttc is None:
            return "—"
        suffix = "/m²" if self.unit == "m2" else ""
        return f"{self.price_ttc:.2f} € TTC{suffix}"

    def is_valid(self) -> tuple[bool, list[str]]:
        """Contrôle minimal de cohérence. Retourne (ok, [problèmes])."""
        problems = []
        if not self.title:
            problems.append("titre manquant")
        if self.price_ttc is None:
            problems.append("prix manquant")
        if self.unit == "m2" and not self.dimensions_cm:
            problems.append("dimensions manquantes pour un produit vendu au m²")
        return (len(problems) == 0, problems)
