---
name: dossier-entreprise
description: Radiographie 360° d'une entreprise française (registre, finances, BODACC, marchés publics, LinkedIn, concurrents, marché, SEO, audit digital) et génération d'un dossier HTML autonome au design Jonction (thème sombre type "Bornet"). Utiliser quand l'utilisateur demande un dossier, un scan ou une fiche sur une entreprise, p. ex. "/dossier-entreprise Briand Villiers-sur-Marne".
---

# Radiographie 360° → dossier HTML (design "Bornet")

Produit un **dossier de prospection complet** sur une entreprise française, au format
**HTML autonome** (`dossier-<slug>.html` à la racine du repo), avec exactement le
design du dossier de référence : `reference-design-bornet.html` (dans ce dossier de
skill) — thème sombre, accent cyan, nav sticky, hero, KPIs, cartes, callouts « bombe ».

`$ARGUMENTS` = nom de l'entreprise + ville/CP, ou un SIREN.

## Organisation du travail

Les étapes 1-4 sont des appels d'API directs (rapides, à faire soi-même via curl).
Les étapes 5-8 sont des recherches web longues : **lancer 2 agents en parallèle**
(Agent, general-purpose) — un pour l'audit digital/LinkedIn/SEO/avis, un pour
concurrents/marché/réglementation — pendant qu'on traite 1-4 et qu'on prépare le HTML.
Exiger des agents des faits chiffrés ET sourcés (URL), avec « non trouvé » explicite
plutôt que des inventions.

## Étape 1 — Registre & groupe

`https://recherche-entreprises.api.gouv.fr/search?q=<nom>&code_postal=<cp>&per_page=25`
(ou `q=<siren>`). Retenir la bonne société (active, effectif/finances). En cas
d'ambiguïté réelle, demander à l'utilisateur.

Noter : SIREN, SIRET siège, dénomination + nom commercial, NAF, création, adresse,
tranche effectif, catégorie, capital, dirigeants (avec années de naissance →
générations), IDCC, certifications (RGE, Qualiopi, UAI…), établissements secondaires
et enseignes, finances incluses.

Puis relancer l'API sur les dirigeants personnes morales (holding) et sur l'adresse
du siège pour cartographier le groupe : holdings, sociétés sœurs, SCI patrimoniales
(les SCI récentes = signal de structuration/transmission).

## Étape 2 — Finances historiques (INPI)

`https://data.economie.gouv.fr/api/records/1.0/search/?dataset=ratios_inpi_bce&q=siren%3D<SIREN>&rows=20`
→ par exercice : CA, résultat net, EBE, marge, liquidité, endettement. Exercices
absents = dépôt confidentiel : le dire, ne pas inventer.

## Étape 3 — BODACC

`https://bodacc-datadila.opendatasoft.com/api/records/1.0/search/?dataset=annonces-commerciales&q=<SIREN>&rows=30&sort=dateparution`
→ procédures collectives (critique), régularité des dépôts, modifications récentes
(administration, capital, siège) avec dates exactes — les modifications récentes sont
des accroches de rendez-vous.

## Étape 4 — Marchés publics (DECP)

`https://data.economie.gouv.fr/api/records/1.0/search/?dataset=decp_augmente&q=<SIREN>&rows=40`
→ **dédupliquer** (l'accord-cadre multi-attributaires apparaît N fois ; un montant
plafond d'accord-cadre n'est pas du CA — le présenter comme plafond). Relever :
nombre de marchés, acheteurs, objets, montants, durées (les 48 mois = récurrence),
années. Signal clé : titulaire actif = terrain AO/bons de commande à automatiser.

## Étape 5 — Audit digital (agent 1)

- **Site** : pages (sitemap.xml, robots.txt), techno (generator WordPress/PHP),
  fraîcheur, blog ou pas, H1/title et mots-clés géo, références/chantiers publiés,
  certifications, coordonnées.
- **Domaine** : `curl -sS https://rdap.nic.fr/domain/<domaine>` → expiration,
  registrar, ancienneté. Chercher aussi anciens domaines/enseignes abandonnés
  (Wayback) : un domaine d'enseigne libre = « bombe » à mettre en avant avec la
  preuve curl.
- **Avis** : Google (note, nombre, taux de réponse du pro, citations textuelles
  d'avis parlants), Indeed/Glassdoor (note employeur = visible des candidats).
- **Réseaux** : LinkedIn (abonnés, effectif déclaré, fréquence posts), Facebook,
  Instagram, X.
- **Offres d'emploi ouvertes** (Indeed, HelloWork, LinkedIn) = douleurs de recrutement.

## Étape 6 — Organigramme LinkedIn (agent 1)

Reconstituer l'équipe : dirigeants, direction (DAF/DRH, directeurs techniques/travaux),
commerce (chargés d'affaires), études/BIM, terrain. Pour chaque personne : nom, poste,
ancienneté si visible. Compter les profils retrouvés vs effectif déclaré. Attention
aux homonymes d'entreprise. Le chiffre choc : « X salariés retrouvés nominativement
sans mettre un pied chez vous ».

## Étape 7 — Concurrents (agent 2)

5-6 acteurs comparables sur la zone, en mix : (a) 1-2 consolidateurs/gros (LBO,
filiales de majors), (b) 2-3 PME familiales quasi-jumelles, (c) ≥1 concurrent au
digital fort. Vérifier CA/effectif de chacun sur recherche-entreprises.api.gouv.fr.
Colonnes : acteur/ville, taille, positionnement, force digitale. Angle narratif :
« le marché se consolide pendant que vous restez indépendants ».

## Étape 8 — Marché & réglementation (agent 2)

Chiffres de la branche (fédérations, Xerfi) : taille, tendance, part de récurrent,
tension de recrutement. 3 réglementations qui créent de la demande ou de la
contrainte pour CE métier (ex. BTP : RE2020, décret tertiaire, interdiction location
passoires, REP bâtiment ; froid : F-Gas, EGalim…). Pour chacune : obligation,
échéance, angle commercial (« → argument de relance »).

## Étape 9 — Écart SEO

Tester ~6 requêtes commerciales locales (métier × zone, dont la ville du siège).
Pour chaque requête : qui capte le trafic (2-3 acteurs) et la cible est-elle
présente/ABSENTE. Compter les pages indexées du site vs concurrents.

## Étape 10 — Générer le dossier HTML

Copier `template.html` (ce dossier de skill) vers `dossier-<slug>.html` et remplir.
Le design est NON NÉGOCIABLE : mêmes variables CSS, même structure que
`reference-design-bornet.html` (thème sombre `#0a0e14`, panneaux `#111823`, accent
cyan `#38bdf8`, ok `#34d399`, warn `#fbbf24`, danger `#fb5b5b`). Fichier 100 %
autonome, aucune ressource externe.

Sections dans l'ordre (nav sticky pointant sur chaque ancre) :
1. **Hero** — « <Nom>, passé au scanner. » + tags (SIREN, ville, ancienneté/génération,
   réseau, IDCC) + date du scan « préparé par Jonction ».
2. **Synthèse express** (`#synth`) — 6 KPIs (CA, résultat, effectif déclaré vs profils
   retrouvés, capital, note employeur, trafic site) + 2 cartes (✅ maison saine /
   🎯 signal stratégique récent).
3. **Société & statuts** (`#legal`) — cartes générations/dirigeants (décideur marqué
   `pill dir DÉCIDEUR`), identité légale, historique BODACC récent.
4. **Organigramme** (`#org`) — grille `person` par pôle (pills DIRECTION/COMMERCE/
   ÉTUDES/TERRAIN), anciennetés, tensions (`⚠ poste en tension`), et la ligne source
   « coût du scan ≈ X € ».
5. **Concurrents** (`#conc`) — tableau 4 colonnes.
6. **Marché & réglementation** (`#marche`) — 4 KPIs marché + 3 cartes réglementation
   avec `→` angle commercial.
7. **Références** (`#refs`) — 3 cartes thématiques des chantiers publiés + le constat
   « contenus déjà payés qui ne rapportent rien » si aucun post/étude de cas.
8. **Marchés publics** (`#marches`) — 3 KPIs (nb marchés, cumul, durées) + tableau
   acheteur/objet/montant. Ne mettre que des montants dédupliqués ; plafonds
   d'accords-cadres signalés comme tels.
9. **Écart SEO** (`#seo`) — tableau requête / qui capte / cible (badge ABSENT rouge)
   + 3 KPIs pages indexées vs concurrents.
10. **Audit digital** (`#digital`) — callouts `bomb` pour les 2-3 découvertes choc
    (domaine expirant/libre avec preuve `curl` en bloc mono, client perdu dans un
    avis, site figé), puis 3 cartes (SEO fantôme / site figé / réputation-réseaux).
11. **Automatisation** (`#axes`) — 5 axes numérotés Jonction, chacun ancré sur une
    douleur RÉELLE trouvée dans le scan (postes ouverts, standard, devis, relances,
    avis/SEO/sourcing) + bloc `pitch` final avec l'argument marché/indépendance et
    l'offre à 1 500 €/mois.
12. **Renforts Jonction** (`#renforts`) — tableau des renforts dédiés mappés sur les
    douleurs trouvées + carte coût (France ~3 800 €/mois vs 1 500 €, −27 600 €/an)
    + carte seuil de rentabilité.
13. **Footer** — méthodologie, date, liste des sources.

Règles : chaque section liste ses sources en `.src` ; chiffres exacts formatés à la
française (`25 729 154 €`, `15,24 M€`) ; jamais de donnée inventée — « non trouvé »
ou omettre ; les affirmations choc doivent avoir une preuve reproductible (commande
curl, URL, citation).

## Étape 11 — Vérifier, committer, livrer

1. Screenshot du rendu (Chromium préinstallé, `executablePath: '/opt/pw-browsers/chromium'`)
   et contrôle visuel (collisions, débordements, sections vides).
2. Comparer section par section avec `reference-design-bornet.html` : chaque section
   de la référence doit exister ou son absence être justifiée (donnée non trouvée).
3. Commit + push sur la branche de travail, puis SendUserFile (display: render).
