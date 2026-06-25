#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generateur de factures JONCTION - pilote par les donnees (multi-clients).

Usage :
    python3 facturation.py clients/<client>.json [--outdir DIR]

Lit `emetteur.json` (Jonction, fixe) + le fichier client, calcule les factures
(forfait mensuel par ressource, prorata en JOURS OUVRES hors feries du pays du
prestataire) et produit les PDF.

Decoupage (client.mission.decoupage) :
  - "mensuel" (defaut) : une facture par mois calendaire, prorata des mois partiels.
  - "global"           : une seule facture pour toute la mission, au forfait plein.

Police Helvetica/latin-1 : accents FR OK, "€" non supporte -> on ecrit "EUR".
Les caracteres hors latin-1 sont assainis automatiquement.
"""
import argparse
import calendar
import json
import os
from datetime import date, timedelta

from fpdf import FPDF, XPos, YPos

BASE = os.path.dirname(os.path.abspath(__file__))

NAVY = (28, 46, 79)
LIGHT = (242, 244, 247)
GREY = (110, 116, 124)
DARK = (33, 37, 41)
LINEC = (210, 214, 220)

L, R = 15, 195
W = R - L

MOIS = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet",
        "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

# Jours feries (best-effort, A VERIFIER / completer par annee).
FERIES_ISO = {
    "FR": {2026: ["2026-01-01", "2026-04-06", "2026-05-01", "2026-05-08",
                  "2026-05-14", "2026-05-25", "2026-07-14", "2026-08-15",
                  "2026-11-01", "2026-11-11", "2026-12-25"]},
    "MG": {2026: ["2026-01-01", "2026-03-29", "2026-04-06", "2026-05-01",
                  "2026-05-14", "2026-05-25", "2026-06-26", "2026-08-15",
                  "2026-11-01", "2026-12-25"]},
}


def latin1_safe(s):
    repl = {"€": "EUR", "—": "-", "–": "-", "’": "'", "‘": "'", "“": '"',
            "”": '"', "œ": "oe", "Œ": "OE", "…": "...", " ": " ",
            " ": " ", "‑": "-"}
    for a, b in repl.items():
        s = s.replace(a, b)
    return s


def parse_d(s):
    y, m, d = (int(x) for x in s.split("-"))
    return date(y, m, d)


def feries_set(pays_list, years):
    out = set()
    for p in pays_list:
        for y in years:
            for iso in FERIES_ISO.get(p, {}).get(y, []):
                out.add(parse_d(iso))
    return out


def jours_ouvres(d1, d2, feries):
    n, d = 0, d1
    while d <= d2:
        if d.weekday() < 5 and d not in feries:
            n += 1
        d += timedelta(days=1)
    return n


def feries_in(d1, d2, feries):
    out, d = [], d1
    while d <= d2:
        if d.weekday() < 5 and d in feries:
            out.append(d)
        d += timedelta(days=1)
    return out


def fmt(n):
    return f"{n:,.2f}".replace(",", " ").replace(".", ",")


def months_between(d1, d2):
    y, m, out = d1.year, d1.month, []
    while (y, m) <= (d2.year, d2.month):
        out.append((y, m))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


# --------------------------------------------------------------- Calcul
def compute_invoices(emetteur, client):
    mi = client["mission"]
    fa = client["facturation"]
    pr = client["prestataire"]
    forfait = float(mi["forfait_mensuel_eur"])          # par ressource / mois
    nb = int(pr.get("nb_ressources", 1))
    libelle = pr.get("libelle", "Prestation d'assistanat commercial")
    unite = pr.get("unite", "personne")
    standard = mi.get("tarif_standard_eur")
    decoupage = mi.get("decoupage", "mensuel")
    pays = pr.get("jours_feries_pays", [])
    b2b = client.get("type", "B2B").upper() == "B2B"
    franchise = fa.get("tva", "franchise") == "franchise"
    ech_j = fa.get("echeance_jours", 30)

    def feries_for(*dts):
        return feries_set(pays, sorted({d.year for d in dts}))

    tnote = ""
    if standard:
        tnote = (f"\nTarif négocié : {fmt(forfait)} EUR HT/{unite} "
                 f"(au lieu de {fmt(float(standard))} EUR HT).")

    def make(num, we, montant, title, detail, periode, mois_min):
        return {
            "num": f"{fa['annee']}-{num:03d}",
            "date": we.strftime("%d/%m/%Y"),
            "echeance": (we + timedelta(days=ech_j)).strftime("%d/%m/%Y"),
            "echeance_jours": ech_j,
            "mois_min": mois_min,
            "periode": periode,
            "title": title,
            "desc": pr["intitule"] + "\n" + pr["horaires"] + "\n" + detail + tnote,
            "montant": montant,
            "nb": nb,
            "tva_franchise": franchise,
            "b2b": b2b,
        }

    invoices = []
    num = fa.get("num_depart", 1)

    if decoupage == "periodes":
        for p in mi["periodes"]:
            ws, we = parse_d(p["debut"]), parse_d(p["fin"])
            feries = feries_for(ws, we)
            montant = round(float(p.get("montant_eur", forfait)) * nb, 2)
            worked = jours_ouvres(ws, we, feries)
            fnote = ", ".join(f"{d.day:02d}/{d.month:02d}"
                              for d in feries_in(ws, we, feries))
            detail = (f"Forfait mensuel - période du {ws.strftime('%d/%m/%Y')} "
                      f"au {we.strftime('%d/%m/%Y')} ({worked} jours ouvrés")
            detail += f", hors {fnote})." if fnote else ")."
            periode = (f"   Période : du {ws.strftime('%d/%m/%Y')} au "
                       f"{we.strftime('%d/%m/%Y')}       "
                       f"Forfait mensuel {fmt(forfait)} EUR HT")
            invoices.append(make(num, we, montant,
                                 f"{libelle} - {MOIS[ws.month]} {ws.year}",
                                 detail, periode, MOIS[ws.month].lower()))
            num += 1
        return invoices

    debut, fin = parse_d(mi["debut"]), parse_d(mi["fin"])
    feries = feries_for(debut, fin)

    if decoupage == "global":
        ws, we = debut, fin
        worked = jours_ouvres(ws, we, feries)
        montant = round(forfait * nb, 2)
        fnote = ", ".join(f"{d.day:02d}/{d.month:02d}"
                          for d in feries_in(ws, we, feries))
        detail = (f"Période : du {ws.strftime('%d/%m/%Y')} au "
                  f"{we.strftime('%d/%m/%Y')} - {worked} jours ouvrés (lun-ven)")
        detail += f", hors {fnote}." if fnote else "."
        periode = (f"   Période : du {ws.strftime('%d/%m/%Y')} au "
                   f"{we.strftime('%d/%m/%Y')}     "
                   f"Forfait mensuel {fmt(forfait)} EUR HT/{unite} x {nb}")
        invoices.append(make(num, we, montant, libelle, detail, periode,
                             "mission"))
        return invoices

    for (y, m) in months_between(debut, fin):
        first = date(y, m, 1)
        last = date(y, m, calendar.monthrange(y, m)[1])
        ws, we = max(debut, first), min(fin, last)
        worked = jours_ouvres(ws, we, feries)
        if worked == 0:
            continue
        full = jours_ouvres(first, last, feries)
        is_full = debut <= first and fin >= last
        montant = (round(forfait * nb, 2) if is_full
                   else round(forfait * nb * worked / full, 2))
        fnote = ", ".join(f"{d.day:02d}/{d.month:02d}"
                          for d in feries_in(ws, we, feries))
        mois_min = MOIS[m].lower()
        if is_full:
            detail = f"Forfait mensuel complet : {worked} jours ouvrés"
            detail += f" (hors {fnote})." if fnote else "."
            extra = ""
        else:
            detail = (f"{worked} jours ouvrés travaillés ({ws.day} au "
                      f"{we.day:02d}/{m:02d}")
            detail += f", hors {fnote}" if fnote else ""
            detail += (f") sur {full} jours ouvrés de {mois_min} : "
                       f"prorata {worked}/{full} du forfait.")
            extra = f" - prorata {worked}/{full} jours ouvrés"
        periode = (f"   Période : du {ws.strftime('%d/%m/%Y')} au "
                   f"{we.strftime('%d/%m/%Y')}       "
                   f"Forfait mensuel {fmt(forfait)} EUR HT{extra}")
        invoices.append(make(num, we, montant, f"{libelle} - {MOIS[m]} {y}",
                             detail, periode, mois_min))
        num += 1
    return invoices


def mentions(emetteur, inv):
    adr = ", ".join(emetteur["adresse"])
    out = (f"Société {emetteur['nom']} - {emetteur['forme']}, au capital de "
           f"{emetteur['capital']}, siège social {adr}. Société en cours "
           f"d'immatriculation au RCS de {emetteur['greffe']} - SIREN en "
           "cours d'attribution.\n"
           f"Facture établie par {emetteur['representant']}, agissant au nom "
           f"et pour le compte de la société {emetteur['nom']} "
           f"({emetteur['forme_courte']}) en formation ; acte destiné à être "
           "repris par la société lors de son immatriculation.\n")
    if inv["tva_franchise"]:
        out += "TVA non applicable, article 293 B du Code général des impôts.\n"
    pen = ("En cas de retard de paiement : pénalités de retard au taux de "
           "trois fois le taux d'intérêt légal, exigibles sans rappel")
    if inv["b2b"]:
        pen += (", et indemnité forfaitaire pour frais de recouvrement de 40 "
                "EUR (art. L441-10 et D441-5 du Code de commerce)")
    pen += ". Aucun escompte pour paiement anticipé."
    return out + pen


# --------------------------------------------------------------- Rendu
def render(path, emetteur, client, inv):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(L, 15, L)
    pdf.add_page()

    def s(x, y):
        pdf.set_xy(x, y)

    def cell(w, h, txt, **kw):
        pdf.cell(w, h, latin1_safe(txt), **kw)

    def mcell(w, h, txt, **kw):
        pdf.multi_cell(w, h, latin1_safe(txt), **kw)

    def hr(y, color=LINEC, width=0.3):
        pdf.set_draw_color(*color)
        pdf.set_line_width(width)
        pdf.line(L, y, R, y)

    pdf.set_text_color(*NAVY)
    pdf.set_font("Helvetica", "B", 24)
    s(L, 15)
    cell(110, 11, emetteur["nom"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GREY)
    s(L, 27)
    cell(110, 5, emetteur["tagline"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_text_color(*NAVY)
    pdf.set_font("Helvetica", "B", 17)
    s(120, 15)
    cell(75, 10, "FACTURE", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    my = 26
    for k, v in [("N° de facture", inv["num"]), ("Date", inv["date"]),
                 ("Échéance", inv["echeance"])]:
        s(120, my)
        pdf.set_text_color(*GREY)
        pdf.set_font("Helvetica", "", 9)
        cell(40, 5, k, align="R")
        pdf.set_text_color(*DARK)
        pdf.set_font("Helvetica", "B", 9)
        cell(35, 5, v, align="R")
        my += 5
    hr(42, NAVY, 0.6)

    def party(x, w, title, lines):
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 8.5)
        s(x, 48)
        cell(w, 6, "  " + title, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        yy = 56
        for txt, bold in lines:
            s(x, yy)
            pdf.set_text_color(*DARK)
            pdf.set_font("Helvetica", "B" if bold else "", 9 if bold else 8.5)
            mcell(w, 4.4, txt, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            yy = pdf.get_y()
        return yy

    em_lines = [(f"{emetteur['nom']} - {emetteur['forme']}", True),
                (f"Capital social : {emetteur['capital']}", False)]
    em_lines += [(a, False) for a in emetteur["adresse"]]
    em_lines += [(f"Tél. : {emetteur['tel']}", False),
                 (f"SIREN : {emetteur['siren_mention']}", False),
                 (f"Représentée par {emetteur['representant']}", False)]
    cl_lines = [(f"{client['raison_sociale']} - {client['forme']}", True),
                (f"Capital social : {client['capital']}", False)]
    cl_lines += [(a, False) for a in client["adresse"]]
    cl_lines += [(f"SIREN : {client['siren']}", False),
                 (f"À l'attention de {client['contact']},", False),
                 (client["contact_role"], False)]
    y1 = party(L, 87, "ÉMETTEUR", em_lines)
    y2 = party(108, 87, "FACTURÉ À", cl_lines)
    ybloc = max(y1, y2) + 4

    pdf.set_fill_color(*LIGHT)
    pdf.set_draw_color(*LINEC)
    pdf.set_text_color(*DARK)
    pdf.set_font("Helvetica", "", 9)
    s(L, ybloc)
    cell(W, 7, inv["periode"], border=1, fill=True,
         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    C_DES, C_QTE, C_PU, C_TOT = 96, 18, 33, 33
    xq, xp, xt = L + C_DES, L + C_DES + C_QTE, L + C_DES + C_QTE + C_PU
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8.5)
    yh = pdf.get_y()
    s(L, yh)
    cell(C_DES, 7, "  DÉSIGNATION", fill=True)
    s(xq, yh)
    cell(C_QTE, 7, "Qté", align="C", fill=True)
    s(xp, yh)
    cell(C_PU, 7, "P.U. HT", align="R", fill=True)
    s(xt, yh)
    cell(C_TOT, 7, "Total HT  ", align="R", fill=True)
    pdf.set_y(yh + 7)

    nbq = inv.get("nb", 1)
    y0 = pdf.get_y() + 1.5
    pdf.set_text_color(*DARK)
    pdf.set_font("Helvetica", "", 9)
    s(xq, y0)
    cell(C_QTE, 5, str(nbq), align="C")
    s(xp, y0)
    cell(C_PU, 5, fmt(inv["montant"] / nbq) + " ", align="R")
    s(xt, y0)
    cell(C_TOT, 5, fmt(inv["montant"]) + " ", align="R")
    pdf.set_font("Helvetica", "B", 9.5)
    s(L + 2, y0)
    cell(C_DES - 2, 5, inv["title"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 8.3)
    pdf.set_text_color(*GREY)
    s(L + 2, pdf.get_y())
    mcell(C_DES - 2, 4.1, inv["desc"], align="L",
          new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    yend = pdf.get_y() + 2
    hr(yend, LINEC, 0.3)
    pdf.set_y(yend + 1)

    pdf.set_text_color(*DARK)
    ytot = pdf.get_y() + 3
    xlab, LBL, VAL = 117, 50, 28

    def trow(lbl, val, fill=False, white=False, bold=False, h=7, size=9):
        y = pdf.get_y()
        if fill:
            pdf.set_fill_color(*NAVY)
        pdf.set_text_color(255, 255, 255) if white else pdf.set_text_color(*DARK)
        pdf.set_font("Helvetica", "B" if bold else "", size)
        s(xlab, y)
        cell(LBL, h, lbl + "  ", align="L", fill=fill)
        s(xlab + LBL, y)
        cell(VAL, h, val + " ", align="R", fill=fill,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(ytot)
    trow("Total HT", fmt(inv["montant"]) + " EUR")
    if inv["tva_franchise"]:
        trow("TVA (non applicable)", "0,00 EUR")
    pdf.ln(0.5)
    trow("NET À PAYER (TTC)", fmt(inv["montant"]) + " EUR",
         fill=True, white=True, bold=True, h=9, size=10.5)

    pdf.set_y(pdf.get_y() + 8)
    hr(pdf.get_y(), LINEC, 0.3)
    pdf.ln(2)

    def block(title, body):
        pdf.set_text_color(*NAVY)
        pdf.set_font("Helvetica", "B", 8.5)
        s(L, pdf.get_y())
        cell(W, 5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*GREY)
        pdf.set_font("Helvetica", "", 7.8)
        s(L, pdf.get_y())
        mcell(W, 3.7, body, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1.5)

    iban = emetteur.get("iban")
    regl = (f"IBAN : {iban} - BIC : {emetteur.get('bic')}." if iban
            else emetteur.get("reglement_note", ""))
    block("Conditions de règlement",
          f"Règlement par virement bancaire. Échéance : {inv['echeance']} "
          f"({inv['echeance_jours']} jours à compter de la date de facture). "
          f"{regl}")
    block("Mentions légales", mentions(emetteur, inv))

    pdf.set_y(-12)
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(*GREY)
    cell(0, 5, f"{emetteur['nom']}  -  Facture N° {inv['num']}  -  Page 1",
         align="C")

    pdf.output(path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("client", help="chemin du JSON client (ex. clients/x.json)")
    ap.add_argument("--outdir", default=BASE)
    args = ap.parse_args()

    with open(os.path.join(BASE, "emetteur.json"), encoding="utf-8") as f:
        emetteur = json.load(f)
    cpath = args.client if os.path.isabs(args.client) else os.path.join(BASE, args.client)
    with open(cpath, encoding="utf-8") as f:
        client = json.load(f)

    invoices = compute_invoices(emetteur, client)
    print(f"Client : {client['raison_sociale']}  ({len(invoices)} facture(s))")
    for inv in invoices:
        out = os.path.join(
            args.outdir,
            f"Facture_{inv['num']}_{client['ref']}_{inv['mois_min']}.pdf")
        render(out, emetteur, client, inv)
        print(f"  {inv['num']}  {inv['title']:<46} {fmt(inv['montant']):>10} EUR"
              f"  -> {os.path.basename(out)}")


if __name__ == "__main__":
    main()
