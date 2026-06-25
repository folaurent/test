# CLAUDE.md — contexte du dépôt

Ce dépôt contient :
- un petit site web statique (`index.html`, `script.js`, `style.css`) ;
- un **module de facturation** dans `factures/`.

---

# Facturation JONCTION

> À lire AVANT de créer/émettre une facture de prestation pour JONCTION.

## 1. Réutiliser ce qui est FIXE (ne pas redemander au client)
Émetteur (Jonction) + conventions détaillées → **`factures/regles-facturation.md`** :
jours ouvrés, prorata des mois partiels, TVA franchise (art. 293 B), mentions
« société en cours de formation », numérotation séquentielle, pénalités de retard
+ indemnité 40 €, feuille de route facturation électronique.

## 2. DEMANDER ce qui dépend du client (impossible à deviner) — fiche d'intake
- [ ] **Client** : raison sociale (ou nom), forme juridique + capital, adresse,
      SIREN/SIRET + RCS (idéalement via **Kbis**), **B2B ou B2C**
      (B2C ⇒ pas d'indemnité 40 €), contact + e-mail.
- [ ] **Prestataire** : qui, **pays** (⇒ jours fériés applicables), horaires (h/jour).
- [ ] **Période** : date de début → date de fin.
- [ ] **Tarif** : forfait négocié (montant + unité, ex. 600 €/mois).
- [ ] **Découpage** : une facture par mois ? prorata en jours ouvrés pour les mois
      partiels.
- [ ] **TVA** : franchise 293 B (défaut 2026) ou régime réel 20 %.
- [ ] **Paramètres** : n° (séquentiel `2026-00X`), date, échéance (défaut 30 j),
      IBAN (si dispo).

## 3. Générer (outil piloté par les données)
- Émetteur fixe : `factures/emetteur.json`. **Un fichier par client** :
  `factures/clients/<client>.json` (modèle : `clients/il-distribution.json`).
- Moteur : `factures/facturation.py` — calcule **tout seul** une facture par mois
  (forfait mensuel, prorata en jours ouvrés hors fériés du pays du prestataire),
  numérote, date, et produit un PDF par mois :
  ```
  cd factures && python3 facturation.py clients/<client>.json
  ```
- **Nouveau client** = créer `clients/<client>.json` (copier le modèle, remplir la
  fiche d'intake du §2) puis lancer la commande. Rien à coder.
- 3 découpages (`mission.decoupage`) : **`mensuel`** (1 facture/mois, prorata des mois
  partiels), **`periodes`** (liste explicite de périodes au forfait plein — ex.
  `clients/il-distribution.json`), **`global`** (1 facture pour toute la mission — ex.
  `clients/pattom.json`). Multi-ressources via `nb_ressources` ; tarif négocié via
  `tarif_standard_eur`.
- Penser à compléter le tableau des **jours fériés** (`FERIES_ISO`) pour chaque
  nouvelle année.
- ⚠️ Police Helvetica/latin-1 : accents FR OK, `€` NON supporté → `EUR` (le moteur
  assainit automatiquement `€ — – ’` …).
- Pas de moteur de rendu image ici : **vérifier en ré-extrayant le texte** (`pypdf`).
- Livrer le PDF (SendUserFile) **et** committer dans `factures/`.
