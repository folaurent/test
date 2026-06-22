# Débrief nuit — Deco & Pro (fiche produit + analyse Romanature)

> Travail réalisé en autonomie (carte blanche) sur le **thème copie NON publié** uniquement
> (« m2 quantite - Claude (preview) », id `200249901404`). **Aucune modification du thème en ligne,
> aucun changement de prix/produit irréversible.** À valider sur l'aperçu, puis tu publies si OK.
>
> Lien aperçu (produit test ARENITE) :
> `https://hyffvf-1f.myshopify.com/products/ca5eareiddaa-arenite?preview_theme_id=200249901404`

---

## 1. Ce qui a été fait cette nuit (sur la copie)

| # | Sujet | État |
|---|---|---|
| 1 | **Zone d'achat « Surface d'abord »** (façon Romanature) : champ Surface en m² −/+ par boîte, « Vendu par X m² », infobulle +5/10 %, **Prix total TTC** dynamique, suit la Taille/Couleur | ✅ sur copie (s'active avec les vraies données) |
| 2 | **Calculateur par variante** (surface/boîte + pièces/boîte stockées **par taille**) | ✅ logique en place + **données TEST** sur ARENITE |
| 3 | **Sélecteur de variantes** type Romanature (lignes « Option : valeur +N Choix » → panneau de cartes vignette+libellé+prix) | ✅ re-hébergé dans `product-variant.liquid` (à revérifier sur mobile) |
| 4 | **Logos faux retirés du carrelage** (« Pierre naturelle / Gel / Légères / Int-Ext ») → affichés **seulement pour le travertin** (collection `pierre-naturelles`) | ✅ |
| 5 | **Doublon de prix supprimé** : la 2ᵉ ligne « 23,80 €/m² » masquée, « /m² » remis sur le prix principal | ✅ |
| 6 | **Image non rognée** : carreau affiché en entier (`object-fit: contain`, cadre carré) | ✅ |
| 7 | **Bandeau entête** : déjà en **français** sur la copie (« Expédition en France sous 48H »). L'anglais visible est sur le **thème publié** (non éditable via l'outil) → corrigé à la publication | ✅ (copie) |

**Fichiers thème modifiés (copie)** : `snippets/product-calculator.liquid`, `snippets/fr-custom-product-quantity.liquid`, `snippets/fr-variant-picker.liquid` (nouveau), `snippets/product-variant.liquid`, `snippets/product-info.liquid`, `snippets/price.liquid`, `snippets/halo-trust-image.liquid`.

⚠️ **Données TEST sur ARENITE** (26 variantes : 30x60→1,44 m²/8 pcs ; 60x60→1,44/4 ; 100x100→1,00/1 ; 60x120→1,44/2 ; 60x90→1,08/2) — **à remplacer par les vraies** via le tableau `..._PAR_TAILLE_A_REMPLIR.xlsx`. Ces valeurs n'apparaissent PAS en ligne (l'ancien thème lit l'ancien champ).

---

## 2. Analyse comparée Romanature vs Deco & Pro (page produit)

| Mesure | Romanature | Deco & Pro | Verdict |
|---|---:|---:|---|
| Poids HTML | **386 Ko** | **1 624 Ko** | 🔴 4,2× plus lourd |
| Balises `<script>` | 66 | **127** | 🔴 |
| Scripts externes | 46 | 56 | 🟠 |
| Feuilles de style | 38 | **52** | 🟠 |
| Blocs `<style>` inline | 2 | **26** | 🟠 |
| Images | 187 | 93 | 🟢 |
| Images sans `alt` | 32 | 2 | 🟢 (toi mieux) |
| `loading=lazy` | 0 | 90 | 🟢 (toi mieux) |
| Données structurées JSON-LD | 4 | 3 | 🟢 ok |
| `<title>` / meta description / canonical / OG | ok | ok | 🟢 |

**Conclusion** : ton SEO de base (title, meta, alt, lazyload, canonical, JSON-LD) est **correct, voire meilleur** que Romanature. Le **vrai problème est la VITESSE** : trop de scripts/apps qui alourdissent la page.

### Apps / scripts détectés sur ta page produit (le « superflu »)
`PageFly` (105 réf.), `shine-trust-v4` (80), `fancybox` (30), `trustoo` (23), `slick` (19), `klaviyo` (11), `facebook pixel` (8), `swiper` (2), `gsap`, `lazysizes`, `tiktok`, `vendor.js`…

➡️ **3 librairies de carrousel/slider en même temps** (slick + swiper + fancybox + gsap) et **PageFly** (page builder très lourd) sont les principaux suspects.

---

## 3. Liste d'améliorations priorisées (pour faire mieux que Romanature)

### 🚀 Vitesse (impact ++, à valider par toi car touche aux apps)
1. **Audit des apps** : désinstaller celles non utilisées. Suspects forts :
   - `PageFly` — si tu n'édites plus de pages avec, il continue de charger 100+ réf. → **désinstaller** libère énormément.
   - `shine-trust-v4` — badges/urgence : 80 réf. Probablement remplaçable par du natif thème (déjà présent).
   - Doublons de sliders : garder **un seul** (le thème a déjà Swiper/Slick) et retirer les apps qui en rechargent.
2. **Pixels marketing** (Facebook, TikTok, Klaviyo) : garder seulement ceux réellement exploités.
3. **Réduire les `<style>` inline (26)** : souvent injectés par apps/sections inutilisées.
4. Activer/vérifier : compression images (WebP), préchargement de la 1ʳᵉ image produit (LCP).

### 🧹 Chasser le superflu (UX, faisable sur la copie)
5. **Faux compteurs d'urgence** : « 10 vendu en dernier 35 heures » et « X personnes regardent » sont des nombres **aléatoires codés** (liste `customer_viewing_number`, `sold_in_number`). Peu crédibles → **à retirer ou rendre honnêtes**.
6. **Lorem ipsum** : le bloc « Caractéristiques » a un **texte lorem ipsum** en repli quand le métachamp est vide → à nettoyer (sinon visible sur produits sans caractéristiques).
7. **Multiples barres d'annonce** : header (3 messages) + barre produit. À rationaliser.
8. **Texte bouton bundle non traduit** : « Get a [discount]% discount buying these products together » (anglais).

### 🔎 SEO (quick wins)
9. **Fil d'ariane en anglais** : « Accueil > **Products** > … » — fallback « Products » codé en dur en JS (devrait être « Produits »).
10. **Double espace dans les `<title>`** : « …| STN  – Deco and pro » (métachamp `title_tag` avec espace en trop).
11. **Onglet « Réalisations »/contenus** : Romanature pousse du contenu (pose, réalisations) → bon pour le SEO longue traîne. À envisager.
12. Vérifier les **balises hreflang** si tu vises FR + Europe (cf. ton bandeau).

### 🛒 Parité Romanature (fonctionnel)
13. **« Commander un échantillon »** (remboursé sur prochaine commande) — à créer (produit « échantillon » + logique).
14. **« Existe aussi en : … »** (renvoi plinthe/format lié).
15. **Blocs réassurance** dépliables (Paiement / Livraison / Retours) avec **tes vraies conditions**.

---

## 4. Bugs trouvés

| Bug | Où | Gravité | Statut |
|---|---|---|---|
| Logos pierre naturelle/gel/etc. affichés sur le carrelage (faux) | bloc trust image | Moyen | ✅ corrigé (copie) |
| Doublon prix « 23,80 € » + « 23,80 €/m² » | `price.liquid` | Moyen | ✅ corrigé (copie) |
| Image produit rognée/zoomée | réglage média | Moyen | ✅ corrigé (copie) |
| Calculateur affichait « 60x60 cm // 0,74 m² » par défaut (faux) sur tout le carrelage | `product-calculator.liquid` | Élevé | ✅ corrigé (copie) |
| Fil d'ariane « Products » en anglais | asset JS | Faible | 📋 à corriger |
| Double espace dans `<title>` | métachamp `title_tag` | Faible | 📋 à corriger (par produit) |
| Lorem ipsum repli bloc Caractéristiques | `templates/product.json` | Faible | 📋 à corriger |
| Texte bundle anglais | réglage section | Faible | 📋 à corriger |
| Bandeau « Shipping… » anglais (thème **publié**) | barre annonce | Faible | ⏳ se corrige à la publication de la copie |

---

## 5. En attente de TOI (décisions / données)

1. **Données surface/pièces par boîte** (tableau `..._PAR_TAILLE_A_REMPLIR.xlsx`) → j'importe + je migre les prix **au m² → à la boîte** (contrainte Shopify : pas de quantités décimales).
2. **Apps à désinstaller** (PageFly, shine-trust, doublons sliders, pixels) → tu confirmes lesquelles.
3. **Cross-sell / Avis** : actuellement **vides** (0 produit lié, 0 avis) → stratégie à définir (auto vs manuel ; collecte d'avis).
4. **Échantillon / réassurance** : valider le mécanisme + tes vraies conditions livraison/paiement/retours.

---

## 6. Prochaines itérations (cette nuit, en boucle)
- Corriger les bugs « faibles » sûrs sur la copie (lorem ipsum, texte bundle anglais, double-espace si faisable globalement).
- Continuer l'audit vitesse (lister précisément les assets supprimables).
- Affiner le sélecteur de variantes et le calculateur.

*Rapport mis à jour à chaque passage de la boucle.*
