---
description: Pont MCP — récupère les données réelles de la boutique Shopify et les injecte dans le système.
---

Récupère des signaux **réels** depuis la boutique Shopify connectée via le
**Shopify MCP** (tu es Claude Code, tu as accès à ces outils), puis écris-les
dans `state/shopify_signals.json`. L'orchestrateur lira ce fichier en priorité
au prochain cycle (précédence : ingéré > API live > simulé), sans appel réseau
de sa part.

Étapes :

1. `mcp__Shopify__get-shop-info` → nom de la boutique, devise, pays.
2. `mcp__Shopify__run-analytics-query` (ShopifyQL) pour les KPI réels, ex. :
   - `FROM sessions SHOW sessions, sessions_with_cart_additions, sessions_that_completed_checkout, conversion_rate SINCE -30d UNTIL today`
   - `FROM sales SHOW orders, total_sales, returning_customer_rate SINCE -30d UNTIL today`
3. Contexte supplémentaire (alimente le bloc `context` + la liste `signals`) :
   - `FROM sessions SHOW sessions GROUP BY referrer_source SINCE -30d UNTIL today ORDER BY sessions DESC`
   - `FROM sessions SHOW sessions GROUP BY session_device_type SINCE -30d UNTIL today`
   - `mcp__Shopify__search_products` (statut, fourchette de prix, types) — pour
     un gros catalogue, utiliser jq sur le fichier de résultat sauvegardé.
4. Écris `state/shopify_signals.json` au format de
   `state/shopify_signals.example.json`. Mappe vers les 4 KPI de l'entreprise :
   `conversion_rate`, `organic_traffic` (= sessions), `cart_abandon_rate`,
   `repeat_purchase_rate`. Remplis aussi `context` (catalogue, sources de
   trafic, appareils, entonnoir) et `signals` (faits saillants pour le CEO).
   Marque `assumption: false` UNIQUEMENT pour les valeurs réellement mesurées ;
   sinon `assumption: true` (pas de fabrication).
5. Lance un cycle : `python orchestrator/orchestrator.py --cycle --dry-run`,
   puis résume le brief (KPI réels vs cibles, file d'approbation).

**Garde-fous** : lecture seule. N'écris JAMAIS dans Shopify (créer/modifier
produit, prix, promo, commande) — ce sont des actions ROUGE qui passent par la
file d'approbation. N'ingère jamais les entités exclues (Sika, Parexlanko).
