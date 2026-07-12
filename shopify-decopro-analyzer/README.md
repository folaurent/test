# Shopify-DecoPro-Analyzer

Outil CLI (Python) qui analyse le catalogue **Deco & Pro** et le compare au
marché concurrentiel pour optimiser prix, cohérence des fiches et SEO/marketing.

## Architecture

```
src/
├── main.py                  # CLI (commandes: load, analyze)
├── models/product.py        # modèle Product (tolérant aux champs inconnus)
├── core/
│   ├── loader/              # lecture JSON / CSV / export Shopify        [code]
│   ├── scraper/             # recherche concurrentielle (Serper/SerpAPI) [sous-agent Recherche]
│   ├── analyzer/            # Price Index + cohérence des specs           [code]
│   └── reporter/            # rapport Markdown / Excel                    [code]
└── agents/orchestrator.py   # 1 pipeline par produit (parallélisable)     [orchestration]
```

**Principe agents/sous-agents** : le code fait le déterministe (lecture, calcul
de prix, rapport) ; les étapes "intelligentes" (recherche web, rédaction
vendeuse/SEO) sont déléguées à des sous-agents branchables (API ou LLM).

## Installation

```bash
pip install -r requirements.txt      # (le module 'load' marche sans dépendances)
cp .env.example .env                 # clés Serper/SerpAPI si scraping en ligne
```

## Utilisation

```bash
# Charger et valider un fichier produits
python -m src.main load data/input/produits_deco.json

# Analyser le catalogue et générer un rapport Markdown
python -m src.main analyze data/input/produits_deco.json --offline
```

Le rapport est écrit dans `data/output/rapport_analyse.md` (5 sections par
produit : description rapide, vendeuse actuelle vs optimisée, tableau de
cohérence, analyse de prix, description marketing alternative).

## Feuille de route
- [x] Loader JSON/CSV + modèle Product + CLI + rapport
- [ ] Scraper : brancher Serper/SerpAPI (recherche + extraction specs)
- [ ] Copywriter : sous-agent de rédaction vendeuse/SEO
- [ ] Reporter : export Excel (xlsx) en plus du Markdown
- [ ] Connecteur Shopify (import direct du catalogue live)

## Sécurité
`.env` jamais commité. Aucune donnée inventée : sans clé API, le scraper
n'ajoute pas de faux prix (il signale simplement l'absence de données).

## Traitement en masse du catalogue STN (Shopify Admin API)

Nécessite `SHOPIFY_STORE` + `SHOPIFY_ADMIN_TOKEN` (app perso, scope `write_products`)
et le tarif STN dans `data/input/` (voir `.env.example`).

```bash
# 1) Enrichir toutes les fiches STN (conditionnement par format, depuis le tarif)
DRY_RUN=1 python -m src.enrich_stn_descriptions   # simulation
DRY_RUN=0 python -m src.enrich_stn_descriptions   # réel

# 2) Archiver les doublons (anciennes fiches mono-format) — sûr : n'archive que
#    si une fiche consolidée existe pour la série
DRY_RUN=1 python -m src.archive_stn_duplicates    # simulation
DRY_RUN=0 python -m src.archive_stn_duplicates    # réel
```
Toujours lancer en `DRY_RUN=1` d'abord et lire le rapport.
