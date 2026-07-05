---
name: dossier-entreprise
description: Scanne une entreprise française (registre, finances, BODACC, web) et génère un dossier HTML autonome. Utiliser quand l'utilisateur demande un dossier, un scan ou une fiche sur une entreprise, p. ex. "/dossier-entreprise Briand Villiers-sur-Marne".
---

# Dossier entreprise → rapport HTML

Génère un dossier complet sur une entreprise française et produit un **fichier HTML autonome** à la racine du repo : `dossier-<slug-entreprise>.html`.

L'argument (`$ARGUMENTS`) contient le nom de l'entreprise, idéalement suivi d'une ville ou d'un code postal, ou directement un SIREN.

## Étape 1 — Identifier l'entreprise

Interroger l'API publique (gratuite, sans clé) :

```
https://recherche-entreprises.api.gouv.fr/search?q=<nom>&code_postal=<cp>&per_page=25
```

- Si un SIREN est fourni, chercher avec `q=<siren>`.
- Retenir la société la plus plausible (active, avec effectif/finances). En cas d'ambiguïté réelle entre plusieurs candidates sérieuses, demander à l'utilisateur.
- Noter : SIREN, SIRET siège, dénomination, NAF, date de création, adresse, tranche d'effectif, catégorie, dirigeants, conventions collectives (IDCC), certifications (RGE, Qualiopi…), finances incluses dans la réponse.
- Relancer la même API sur les dirigeants personnes morales (holding) pour cartographier le groupe : autres sociétés à la même adresse ou avec le même président.

## Étape 2 — Finances historiques (INPI)

```
https://data.economie.gouv.fr/api/records/1.0/search/?dataset=ratios_inpi_bce&q=siren%3D<SIREN>&rows=20
```

Extraire par exercice : `date_cloture_exercice`, `chiffre_d_affaires`, `resultat_net`, `ebe`, `marge_brute`, `ratio_de_liquidite`, `taux_d_endettement`. Les exercices absents sont généralement déposés en confidentiel — le signaler, ne pas inventer.

## Étape 3 — Historique juridique (BODACC)

```
https://bodacc-datadila.opendatasoft.com/api/records/1.0/search/?dataset=annonces-commerciales&q=<SIREN>&rows=30&sort=dateparution
```

Relever : procédures collectives (point critique), régularité des dépôts de comptes, modifications (siège, gouvernance), date de la dernière annonce.

## Étape 4 — Web

- WebSearch sur `"<nom>" <ville> entreprise` : site officiel, actualités, litiges éventuels.
- WebFetch du site officiel : activités, références, certifications, zone d'intervention.
- Si le connecteur Pappers a des crédits, l'utiliser en complément (dirigeants détaillés, bénéficiaires effectifs, cartographie) ; sinon s'en tenir aux sources ci-dessus.

## Étape 5 — Générer le rapport HTML

Copier `template.html` (dans ce dossier de skill) vers `dossier-<slug>.html` à la racine du repo et remplacer les contenus. Le fichier doit rester **100 % autonome** (CSS inline, aucune ressource externe) et gérer les thèmes clair/sombre.

Sections obligatoires, dans cet ordre :
1. **En-tête** : dénomination, SIREN, adresse, badge d'état (en activité / cessée / procédure collective), date du scan.
2. **Chiffres clés** (tuiles) : CA du dernier exercice public, résultat net, effectif, ancienneté.
3. **Fiche d'identité** (tableau).
4. **Activité** : métiers, certifications.
5. **Gouvernance** : dirigeants, CAC.
6. **Finances** : tableau par exercice + lecture en 3-4 puces.
7. **Groupe** : entités liées (tableau) si pertinent.
8. **Historique BODACC** : synthèse, mention explicite « aucune procédure collective » ou détail des procédures.
9. **Synthèse** : points forts / points de vigilance (inclure les homonymes à ne pas confondre).
10. **Sources** : liens cliquables vers chaque source utilisée.

Règles :
- Formater les montants en euros avec séparateurs d'espace (`25 729 154 €`).
- Ne jamais présenter une donnée non sourcée ; marquer « n.d. » ce qui manque.
- Terminer en commitant le fichier HTML sur la branche de travail, en le poussant, puis en l'envoyant à l'utilisateur avec SendUserFile (display: render).
