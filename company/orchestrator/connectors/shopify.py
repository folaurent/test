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

# Pont MCP : fichier de signaux déposé par Claude Code (via le Shopify MCP).
# L'orchestrateur le lit sans faire d'appel réseau lui-même — la récupération
# a déjà eu lieu côté agent interactif. Précédence : ingéré > API live > simulé.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INGEST_PATH = os.path.join(ROOT, "state", "shopify_signals.json")
# Seed versionné (réel, embarqué dans le repo) : sert de repli quand aucun
# fichier ingéré "live" n'est présent (ex. déploiement frais sur un VPS).
SEED_PATH = os.path.join(ROOT, "state", "shopify_signals.seed.json")


def configured() -> bool:
    return bool(os.environ.get("SHOPIFY_STORE_DOMAIN") and os.environ.get("SHOPIFY_ADMIN_TOKEN"))


def has_ingested() -> bool:
    return os.path.exists(INGEST_PATH)


def status() -> str:
    if has_ingested():
        try:
            with open(INGEST_PATH, encoding="utf-8") as f:
                src = json.load(f).get("source", "ingested")
            return f"ingested via MCP ({src})"
        except Exception:
            return "ingested file present (unreadable)"
    if configured():
        return f"configured ({os.environ['SHOPIFY_STORE_DOMAIN']})"
    if os.path.exists(SEED_PATH):
        return "seed (real data embedded in repo)"
    return "not configured (using simulated data)"


def _read_signals_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data.get("kpis") is not None:
            return data
    except Exception:
        return None
    return None


def _ingested_signals():
    """Lit les signaux déposés par le pont MCP (live), si présents et valides."""
    return _read_signals_file(INGEST_PATH) if has_ingested() else None


def _seed_signals():
    """Lit le seed versionné (réel) embarqué dans le repo, si présent."""
    return _read_signals_file(SEED_PATH) if os.path.exists(SEED_PATH) else None


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
    Précédence :
      1. Fichier ingéré via le pont MCP (state/shopify_signals.json) — données
         réelles déposées par Claude Code, utilisables même en dry-run car
         l'orchestrateur ne fait aucun appel réseau.
      2. API Admin live (configuré + --live).
      3. Données simulées.
    """
    ingested = _ingested_signals()
    if ingested:
        return ingested

    if dry_run or not configured():
        # Repli : seed réel versionné si dispo, sinon simulé.
        return _seed_signals() or _simulated_signals()

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
