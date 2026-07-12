"""
Shopify-DecoPro-Analyzer — point d'entrée CLI.

Exemples :
    python -m src.main load   data/input/produits_deco.json
    python -m src.main analyze data/input/produits_deco.json
"""
from __future__ import annotations

import argparse
import sys

from src.core.loader.loader import load_products, summarize, LoaderError
from src.agents.orchestrator import analyze_catalog
from src.core.reporter.reporter import write_report


def cmd_load(args) -> int:
    try:
        products = load_products(args.source)
    except LoaderError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    s = summarize(products)
    print(f"✅ {s['total']} produits chargés depuis {args.source}")
    print(f"   • Valides : {s['valides']}   • Avec alertes : {s['avec_alertes']}")
    print(f"   • Catégories : {', '.join(s['categories']) or '—'}\n")
    for p in products:
        ok, problems = p.is_valid()
        flag = "✅" if ok else "⚠️ "
        note = "" if ok else f"  ({', '.join(problems)})"
        print(f"  {flag} {p.title:<45} {p.price_label:>16}{note}")
    return 0


def cmd_analyze(args) -> int:
    try:
        products = load_products(args.source)
    except LoaderError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    print(f"🔎 Analyse de {len(products)} produits (mode "
          f"{'hors-ligne' if args.offline else 'en ligne'})...")
    results = analyze_catalog(products)
    path = write_report([r.markdown for r in results], out_dir=args.out)
    alerts = sum(len(r.alerts) for r in results)
    print(f"📝 Rapport écrit : {path}")
    print(f"   • Produits analysés : {len(results)}   • Alertes de cohérence : {alerts}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="decopro-analyzer",
                                description="Analyse concurrentielle du catalogue Deco & Pro")
    sub = p.add_subparsers(dest="command", required=True)

    pl = sub.add_parser("load", help="Charger et valider un fichier produits")
    pl.add_argument("source", help="Chemin .json ou .csv")
    pl.set_defaults(func=cmd_load)

    pa = sub.add_parser("analyze", help="Analyser le catalogue et générer un rapport")
    pa.add_argument("source", help="Chemin .json ou .csv")
    pa.add_argument("--out", default="data/output", help="Dossier de sortie")
    pa.add_argument("--offline", action="store_true",
                    help="Ne pas interroger les API de recherche")
    pa.set_defaults(func=cmd_analyze)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
