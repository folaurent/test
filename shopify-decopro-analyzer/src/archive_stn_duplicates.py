#!/usr/bin/env python3
"""
Archivage sûr des doublons STN sur Shopify.
--------------------------------------------
Beaucoup de séries STN existent en double : une fiche "consolidée"
(ex. « Carrelage Amstel », multi-variantes) + d'anciennes fiches mono-format
(ex. « Carrelage  BALNEA NATURAL MT 120X280 RECT. », 1 variante).

Ce script archive UNIQUEMENT les anciennes fiches quand une version consolidée
existe pour la même série. Règle de sécurité :

  Pour chaque série (1er mot après "Carrelage"), on cherche LA fiche consolidée
  = titre « Carrelage <Série> » (sans dimension dans le titre) ET >= 2 variantes.
    - si exactement une consolidée existe -> on archive les AUTRES fiches actives
      de la série (les mono-format / doublons) ;
    - sinon (aucune, ou plusieurs candidates ambiguës) -> on NE TOUCHE À RIEN
      et on le signale dans le rapport.

Rien n'est jamais archivé pour une série qui n'a qu'une seule fiche.

Usage :
    DRY_RUN=1 python -m src.archive_stn_duplicates   # simulation + rapport
    DRY_RUN=0 python -m src.archive_stn_duplicates   # archivage réel

.env : SHOPIFY_STORE, SHOPIFY_ADMIN_TOKEN (scope write_products).
"""
from __future__ import annotations

import os
import re
import time
from collections import defaultdict

import requests
from dotenv import load_dotenv

load_dotenv()

DRY_RUN = os.getenv("DRY_RUN", "1") == "1"
STORE = os.environ.get("SHOPIFY_STORE", "")
TOKEN = os.environ.get("SHOPIFY_ADMIN_TOKEN", "")
API = f"https://{STORE}/admin/api/2024-10/graphql.json"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

DIM = re.compile(r"\d+\s*[xX]\s*\d+")  # une dimension dans le titre => ancienne fiche


def gql(query: str, variables: dict | None = None) -> dict:
    r = requests.post(API, headers=HEADERS,
                      json={"query": query, "variables": variables or {}}, timeout=30)
    r.raise_for_status()
    d = r.json()
    if d.get("errors"):
        raise RuntimeError(d["errors"])
    return d["data"]


def list_products() -> list[dict]:
    out, cursor = [], None
    q = """
    query($cursor: String) {
      products(first: 100, after: $cursor, query: "vendor:'STN Ceramica' status:active") {
        edges { cursor node { id title variantsCount { count } } }
        pageInfo { hasNextPage }
      }
    }"""
    while True:
        d = gql(q, {"cursor": cursor})
        edges = d["products"]["edges"]
        out += [e["node"] for e in edges]
        if not d["products"]["pageInfo"]["hasNextPage"]:
            break
        cursor = edges[-1]["cursor"]
    return out


ARCHIVE = """
mutation($id: ID!) {
  productUpdate(product: {id: $id, status: ARCHIVED}) {
    product { id }
    userErrors { field message }
  }
}"""


def series_of(title: str) -> str:
    t = re.sub(r"^carrelage\s+", "", title.strip(), flags=re.I)
    return t.split()[0].upper() if t.split() else ""


def is_consolidated(p: dict) -> bool:
    """Titre « Carrelage <Série> » sans dimension ET au moins 2 variantes."""
    title = p["title"]
    body = re.sub(r"^carrelage\s+", "", title.strip(), flags=re.I)
    no_dim = not DIM.search(title)
    single_series = len(body.split()) <= 2  # tolère 2 mots (ex "Dolce Vita")
    return no_dim and single_series and p["variantsCount"]["count"] >= 2


def main():
    if not STORE or not TOKEN:
        raise SystemExit("Renseigne SHOPIFY_STORE et SHOPIFY_ADMIN_TOKEN dans .env")
    print(f"=== Archivage doublons STN — {'SIMULATION' if DRY_RUN else 'REEL'} ===")
    prods = list_products()
    print(f"{len(prods)} produits STN actifs.\n")

    groups = defaultdict(list)
    for p in prods:
        groups[series_of(p["title"])].append(p)

    to_archive, ambiguous, singletons = [], [], 0
    for serie, items in groups.items():
        if len(items) < 2:
            singletons += 1
            continue
        consolidated = [p for p in items if is_consolidated(p)]
        if len(consolidated) != 1:
            ambiguous.append((serie, [p["title"] for p in items]))
            continue
        keep = consolidated[0]
        for p in items:
            if p["id"] != keep["id"]:
                to_archive.append((serie, p, keep))

    print(f"À archiver : {len(to_archive)} doublons\n")
    for serie, p, keep in to_archive:
        print(f"  {serie:12} archive « {p['title']} »  (garde « {keep['title']} »)")
        if not DRY_RUN:
            d = gql(ARCHIVE, {"id": p["id"]})
            errs = d["productUpdate"]["userErrors"]
            if errs:
                print(f"     ⚠️ {errs}")
            time.sleep(0.3)

    print("\n========== RAPPORT ==========")
    print(f"Doublons {'à archiver (simulé)' if DRY_RUN else 'archivés'} : {len(to_archive)}")
    print(f"Séries uniques (intactes) : {singletons}")
    if ambiguous:
        print(f"Séries ambiguës (NON touchées, à vérifier à la main) : {len(ambiguous)}")
        for serie, titles in ambiguous:
            print(f"  - {serie} : {titles}")
    if DRY_RUN:
        print("\n👉 Simulation. Mets DRY_RUN=0 pour archiver réellement.")


if __name__ == "__main__":
    main()
