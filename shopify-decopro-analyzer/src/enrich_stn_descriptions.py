#!/usr/bin/env python3
"""
Enrichissement en masse des fiches STN sur Shopify.
-----------------------------------------------------
Parcourt TOUT le catalogue STN et réécrit la description de chaque produit avec
un tableau "conditionnement par format" (m²/boîte, kg/boîte) issu du TARIF STN
officiel — la source de vérité.

Pourquoi un script (et pas le chat) :
  - le tarif est parsé proprement avec openpyxl (gère les virgules/quotes des
    formats, ce que l'extraction "à plat" ratait sur certaines séries) ;
  - les mises à jour passent par l'API Admin en renvoyant le strict minimum
    (id) → coût quasi nul, insensible aux coupures, reprenable.

Usage :
    DRY_RUN=1 python -m src.enrich_stn_descriptions   # simulation + rapport
    DRY_RUN=0 python -m src.enrich_stn_descriptions   # exécution réelle

.env attendu :
    SHOPIFY_STORE=hyffvf-1f.myshopify.com
    SHOPIFY_ADMIN_TOKEN=shpat_xxx        # app personnalisée, scope write_products
    TARIF_XLSX=./data/input/LISTE_PRIX_STN_2024.xlsx
"""
from __future__ import annotations

import os
import re
import json
import time
import unicodedata

import requests
from dotenv import load_dotenv
from openpyxl import load_workbook

load_dotenv()

DRY_RUN = os.getenv("DRY_RUN", "1") == "1"
STORE = os.environ.get("SHOPIFY_STORE", "")
TOKEN = os.environ.get("SHOPIFY_ADMIN_TOKEN", "")
TARIF = os.getenv("TARIF_XLSX", "./data/input/LISTE_PRIX_STN_2024.xlsx")
API = f"https://{STORE}/admin/api/2024-10/graphql.json"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}


# --------------------------------------------------------------------------- #
#  1) Parser le tarif STN (source de vérité) — proprement, via openpyxl
# --------------------------------------------------------------------------- #
def norm(s) -> str:
    s = "" if s is None else str(s)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return s.strip().lower()


def parse_tarif(path: str) -> dict:
    """Retourne {SERIE: {format: {'m2': float, 'kg': float, 'ttc': float|None}}}."""
    wb = load_workbook(path, read_only=True, data_only=True)
    specs: dict[str, dict] = {}
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        # repérer la ligne d'en-tête (contient "serie" et "format" et "m2/boite")
        header_idx = None
        for i, r in enumerate(rows):
            cells = [norm(c) for c in r]
            if any("serie" in c for c in cells) and any("format" in c for c in cells):
                header_idx = i
                header = cells
                break
        if header_idx is None:
            continue

        def col(*keys):
            for j, c in enumerate(header):
                if all(k in c for k in keys):
                    return j
            return None

        ci = {
            "serie": col("serie"), "format": col("format"),
            "m2": col("m2", "boite") or col("m2", "boi"),
            "kg": col("kg", "boite") or col("kg", "boi"),
            "ttc": col("ttc") or col("prix", "vente", "ttc"),
        }
        if ci["serie"] is None or ci["format"] is None:
            continue
        for r in rows[header_idx + 1:]:
            def val(key):
                j = ci[key]
                return r[j] if (j is not None and j < len(r)) else None
            serie = (str(val("serie")).strip().upper() if val("serie") else "")
            fmt = (str(val("format")).strip() if val("format") else "")
            if not serie or not fmt:
                continue
            def num(x):
                if x is None:
                    return None
                m = re.search(r"[\d.,]+", str(x))
                return float(m.group().replace(",", ".")) if m else None
            specs.setdefault(serie, {})[fmt] = {
                "m2": num(val("m2")), "kg": num(val("kg")), "ttc": num(val("ttc")),
            }
    wb.close()
    return specs


# --------------------------------------------------------------------------- #
#  2) Générer la description enrichie d'une série
# --------------------------------------------------------------------------- #
def clean_fmt(f: str) -> str:
    f = f.replace("RECT.", "").replace("PUL.", "poli").strip()
    f = re.sub(r"\s+", " ", f)
    return f


def build_description(serie: str, formats: dict) -> str:
    title = serie.title()
    rows = ""
    for f, v in sorted(formats.items()):
        if v.get("m2") is None:
            continue
        kg = f"{v['kg']:.1f}".replace(".", ",") if v.get("kg") else "—"
        m2 = f"{v['m2']:.2f}".replace(".", ",")
        rows += (f'<tr><td style="padding:6px 8px">{clean_fmt(f)}</td>'
                 f'<td style="padding:6px 8px">{m2}</td>'
                 f'<td style="padding:6px 8px">{kg}</td></tr>')
    if not rows:
        return ""  # pas de specs fiables -> on ne touche pas la fiche
    fmt_list = " · ".join(sorted({clean_fmt(f) for f in formats}))
    return (
        f'<h2>Carrelage {title} – Grès cérame rectifié (STN)</h2>'
        f'<p>Carrelage en <strong>grès cérame rectifié</strong> de la collection '
        f'<strong>{title}</strong> (STN). Formats disponibles : {fmt_list}.</p>'
        f'<h3 style="margin-top:14px">Conditionnement par format</h3>'
        f'<table style="border-collapse:collapse;width:100%;font-size:0.9em">'
        f'<tr style="background:#f5f5f5;font-weight:bold">'
        f'<td style="padding:6px 8px">Format</td><td style="padding:6px 8px">m² / boîte</td>'
        f'<td style="padding:6px 8px">kg / boîte</td></tr>{rows}</table>'
        f'<p style="font-size:0.8em;color:#777;margin-top:6px">Vendu au m² · commande par '
        f'boîte entière · prévoyez ~5 % de perte à la coupe · sur commande, '
        f'livré sous ~10 jours. Conditionnements : tarif officiel STN.</p>'
    )


# --------------------------------------------------------------------------- #
#  3) Shopify Admin API : lister les produits STN + mettre à jour
# --------------------------------------------------------------------------- #
def gql(query: str, variables: dict | None = None) -> dict:
    r = requests.post(API, headers=HEADERS,
                      json={"query": query, "variables": variables or {}}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data["data"]


def list_stn_products() -> list[dict]:
    out, cursor = [], None
    q = """
    query($cursor: String) {
      products(first: 100, after: $cursor, query: "vendor:'STN Ceramica' status:active") {
        edges { cursor node { id title } }
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


UPDATE = """
mutation($id: ID!, $html: String!) {
  productUpdate(product: {id: $id, descriptionHtml: $html}) {
    product { id }
    userErrors { field message }
  }
}"""


def series_from_title(title: str) -> str:
    # "Carrelage Arenite" -> "ARENITE"
    t = re.sub(r"^carrelage\s+", "", title.strip(), flags=re.I)
    return t.strip().upper()


def main():
    if not STORE or not TOKEN:
        raise SystemExit("Renseigne SHOPIFY_STORE et SHOPIFY_ADMIN_TOKEN dans .env")
    print(f"=== Enrichissement STN — {'SIMULATION' if DRY_RUN else 'REEL'} ===")
    specs = parse_tarif(TARIF)
    print(f"Tarif : {len(specs)} séries chargées.")
    products = list_stn_products()
    print(f"Boutique : {len(products)} produits STN actifs.\n")

    done, skipped_no_spec, errors = [], [], []
    for p in products:
        serie = series_from_title(p["title"])
        formats = specs.get(serie)
        if not formats:
            skipped_no_spec.append(serie)
            continue
        html = build_description(serie, formats)
        if not html:
            skipped_no_spec.append(serie)
            continue
        if DRY_RUN:
            done.append(serie)
            print(f"[SIM] {serie:14} ({len([f for f in formats if formats[f].get('m2')])} formats)")
            continue
        d = gql(UPDATE, {"id": p["id"], "html": html})
        errs = d["productUpdate"]["userErrors"]
        if errs:
            errors.append((serie, errs))
            print(f"  ⚠️ {serie}: {errs}")
        else:
            done.append(serie)
            print(f"  ✅ {serie}")
        time.sleep(0.3)  # respect rate limit

    print("\n========== RAPPORT ==========")
    print(f"Enrichis : {len(done)}")
    print(f"Sans specs au tarif (ignorés, non modifiés) : {len(set(skipped_no_spec))}")
    if skipped_no_spec:
        print("  →", ", ".join(sorted(set(skipped_no_spec))))
    if errors:
        print(f"Erreurs : {len(errors)}")
    if DRY_RUN:
        print("\n👉 Simulation. Mets DRY_RUN=0 pour appliquer réellement.")


if __name__ == "__main__":
    main()
