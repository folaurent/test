"""
shopify.py — connecteur de données e-commerce réelles (Shopify Admin GraphQL).

Lecture seule. Lit la boutique via l'API Admin GraphQL en utilisant :
  SHOPIFY_STORE_DOMAIN   ex. "ma-boutique.myshopify.com"
  SHOPIFY_ADMIN_TOKEN    jeton d'accès Admin API (Bearer / X-Shopify-Access-Token)

Garde-fous :
  - Lecture seule : ce connecteur n'écrit JAMAIS. Toute écriture (créer un
    produit, modifier un prix, lancer une promo) reste une action ROUGE qui
    passe par la file d'approbation.
  - En dry-run, AUCUN appel réseau : on renvoie des signaux simulés.
  - Pas de fabrication : un KPI que l'Admin API ne mesure pas réellement
    (ex. taux de conversion, qui nécessite l'analytics de sessions) est
    renvoyé marqué `assumption=True` plutôt que présenté comme un fait.
"""

from __future__ import annotations

import json
import os
import urllib.request

API_VERSION = "2024-10"


def configured() -> bool:
    return bool(os.environ.get("SHOPIFY_STORE_DOMAIN") and os.environ.get("SHOPIFY_ADMIN_TOKEN"))


def status() -> str:
    if configured():
        return f"configured ({os.environ['SHOPIFY_STORE_DOMAIN']})"
    return "not configured (using simulated data)"


def _graphql(query: str) -> dict:
    domain = os.environ["SHOPIFY_STORE_DOMAIN"]
    token = os.environ["SHOPIFY_ADMIN_TOKEN"]
    url = f"https://{domain}/admin/api/{API_VERSION}/graphql.json"
    data = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "X-Shopify-Access-Token": token},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


# Requête minimale et robuste : compteurs + 5 dernières commandes.
_QUERY = """
{
  shop { name currencyCode }
  productsCount { count }
  customersCount { count }
  ordersCount { count }
  orders(first: 5, sortKey: CREATED_AT, reverse: true) {
    edges { node { id createdAt currentTotalPriceSet { shopMoney { amount } } } }
  }
}
"""


def _simulated_signals() -> dict:
    """Signaux synthétiques déterministes — repli sans dépendance externe."""
    return {
        "source": "simulated",
        "kpis": [
            {"name": "conversion_rate", "value": 1.6, "unit": "%", "assumption": True},
            {"name": "organic_traffic", "value": 6300, "unit": "visits", "assumption": True},
            {"name": "cart_abandon_rate", "value": 68, "unit": "%", "assumption": True},
            {"name": "repeat_purchase_rate", "value": 16, "unit": "%", "assumption": True},
        ],
        "signals": [
            "Catalogue : ~120 produits (simulé)",
            "Commandes 30j : ~340 (simulé)",
        ],
    }


def fetch_signals(dry_run: bool = True) -> dict:
    """
    Renvoie {source, kpis:[{name,value,unit,assumption}], signals:[...]}.
    - dry-run OU non configuré -> données simulées (aucun appel réseau).
    - configuré + live -> lecture réelle Shopify, dérivation prudente des KPI.
    """
    if dry_run or not configured():
        return _simulated_signals()

    try:
        payload = _graphql(_QUERY)
        data = payload.get("data") or {}
    except Exception as e:
        sim = _simulated_signals()
        sim["source"] = f"simulated (shopify error: {type(e).__name__})"
        return sim

    products = (data.get("productsCount") or {}).get("count", 0)
    customers = (data.get("customersCount") or {}).get("count", 0)
    orders = (data.get("ordersCount") or {}).get("count", 0)
    shop_name = (data.get("shop") or {}).get("name", "?")

    # Dérivations prudentes. L'Admin API ne fournit pas le trafic de sessions
    # ni le taux de conversion sans l'API Analytics — on les marque assumption.
    repeat_rate = round((customers and orders > customers) and
                        min(100, 100 * (orders - customers) / max(orders, 1)) or 0.0, 2)

    return {
        "source": f"shopify:{shop_name}",
        "kpis": [
            {"name": "conversion_rate", "value": 0.0, "unit": "%", "assumption": True,
             "note": "nécessite l'API Analytics (sessions) — non mesuré ici"},
            {"name": "organic_traffic", "value": 0.0, "unit": "visits", "assumption": True,
             "note": "nécessite l'API Analytics — non mesuré ici"},
            {"name": "cart_abandon_rate", "value": 0.0, "unit": "%", "assumption": True,
             "note": "nécessite les checkouts abandonnés — non mesuré ici"},
            {"name": "repeat_purchase_rate", "value": repeat_rate, "unit": "%",
             "assumption": True, "note": "proxy = (commandes - clients) / commandes"},
        ],
        "signals": [
            f"Catalogue : {products} produits (réel)",
            f"Clients : {customers} (réel)",
            f"Commandes (total) : {orders} (réel)",
        ],
    }
