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

## 3. Générer
- Script : `factures/gen_facture.py` (fpdf2).
- ⚠️ Police Helvetica/latin-1 : **accents FR OK**, mais **symbole € NON supporté**
  → écrire `EUR`. Tirets longs `—`/`–` et apostrophes typographiques `’` interdits
  (hors latin-1) → utiliser `-` et `'`.
- Pas de moteur de rendu image ici : **vérifier en ré-extrayant le texte** du PDF
  (`pypdf`).
- Livrer le PDF (SendUserFile) **et** committer dans `factures/`.
