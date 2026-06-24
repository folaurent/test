#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generateur de factures JONCTION -> IL DISTRIBUTION.
Deux factures mensuelles : 2026-001 (juin) et 2026-002 (juillet).
Police Helvetica/latin-1 : accents FR OK, symbole € non supporte -> "EUR".
Version TVA : franchise en base (art. 293 B) -> TVA 0. Parametrable."""
from fpdf import FPDF, XPos, YPos

NAVY  = (28, 46, 79)
LIGHT = (242, 244, 247)
GREY  = (110, 116, 124)
DARK  = (33, 37, 41)
LINEC = (210, 214, 220)

L = 15
R = 195
W = R - L

DIR = "/tmp/claude-0/-home-user-test/43c352ac-163d-57f4-a078-981cdd903364/scratchpad/"


class Facture(FPDF):
    inv_num = ""
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*GREY)
        self.cell(0, 5, f"JONCTION  -  Facture N° {self.inv_num}  -  "
                  f"Page {self.page_no()}", align="C")


EMETTEUR = [
    ("JONCTION - SAS en cours de formation", True),
    ("Capital social : 500 EUR", False),
    ("59, rue de Ponthieu", False),
    ("75008 Paris", False),
    ("Tél. : +33 6 27 89 37 42", False),
    ("SIREN : en cours d'immatriculation (RCS de Paris)", False),
    ("Représentée par M. Laurent FOURNIER", False),
]
CLIENT = [
    ("IL DISTRIBUTION - SAS à associé unique", True),
    ("Capital social : 131 000 EUR", False),
    ("42, rue de Maisse", False),
    ("91820 Boutigny-sur-Essonne", False),
    ("SIREN : 912 232 832 - RCS Evry", False),
    ("À l'attention de Mme Jennifer DA COSTA ALVES,", False),
    ("Présidente", False),
]


def build(cfg):
    pdf = Facture(orientation="P", unit="mm", format="A4")
    pdf.inv_num = cfg["num"]
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(L, 15, L)
    pdf.add_page()

    def sx(x, y):
        pdf.set_xy(x, y)

    def hr(y, color=LINEC, width=0.3):
        pdf.set_draw_color(*color)
        pdf.set_line_width(width)
        pdf.line(L, y, R, y)

    # ---- en-tete
    pdf.set_text_color(*NAVY)
    pdf.set_font("Helvetica", "B", 24)
    sx(L, 15)
    pdf.cell(110, 11, "JONCTION", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*GREY)
    sx(L, 27)
    pdf.cell(110, 5, "Prestations d'assistanat commercial",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_text_color(*NAVY)
    pdf.set_font("Helvetica", "B", 17)
    sx(120, 15)
    pdf.cell(75, 10, "FACTURE", align="R", new_x=XPos.LMARGIN,
             new_y=YPos.NEXT)
    meta = [("N° de facture", cfg["num"]), ("Date", cfg["date"]),
            ("Échéance", cfg["echeance"])]
    my = 26
    for k, v in meta:
        sx(120, my)
        pdf.set_text_color(*GREY); pdf.set_font("Helvetica", "", 9)
        pdf.cell(40, 5, k, align="R")
        pdf.set_text_color(*DARK); pdf.set_font("Helvetica", "B", 9)
        pdf.cell(35, 5, v, align="R")
        my += 5
    hr(42, NAVY, 0.6)

    # ---- parties
    def party(x, w, title, lines):
        pdf.set_fill_color(*NAVY); pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 8.5)
        sx(x, 48)
        pdf.cell(w, 6, "  " + title, fill=True, new_x=XPos.LMARGIN,
                 new_y=YPos.NEXT)
        yy = 56
        for txt, bold in lines:
            sx(x, yy)
            pdf.set_text_color(*DARK)
            pdf.set_font("Helvetica", "B" if bold else "",
                         9 if bold else 8.5)
            pdf.multi_cell(w, 4.4, txt, align="L", new_x=XPos.LMARGIN,
                           new_y=YPos.NEXT)
            yy = pdf.get_y()
        return yy

    y1 = party(L, 87, "ÉMETTEUR", EMETTEUR)
    y2 = party(108, 87, "FACTURÉ À", CLIENT)
    ybloc = max(y1, y2) + 4

    # ---- periode
    pdf.set_fill_color(*LIGHT); pdf.set_draw_color(*LINEC)
    pdf.set_text_color(*DARK); pdf.set_font("Helvetica", "", 9)
    sx(L, ybloc)
    pdf.cell(W, 7, cfg["periode"], border=1, fill=True,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    # ---- tableau
    C_DES, C_QTE, C_PU, C_TOT = 96, 18, 33, 33
    xq, xp, xt = L + C_DES, L + C_DES + C_QTE, L + C_DES + C_QTE + C_PU
    pdf.set_fill_color(*NAVY); pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8.5)
    yh = pdf.get_y()
    sx(L, yh);  pdf.cell(C_DES, 7, "  DÉSIGNATION", fill=True)
    sx(xq, yh); pdf.cell(C_QTE, 7, "Qté", align="C", fill=True)
    sx(xp, yh); pdf.cell(C_PU, 7, "P.U. HT", align="R", fill=True)
    sx(xt, yh); pdf.cell(C_TOT, 7, "Total HT  ", align="R", fill=True)
    pdf.set_y(yh + 7)

    for it in cfg["items"]:
        y0 = pdf.get_y() + 1.5
        pdf.set_text_color(*DARK); pdf.set_font("Helvetica", "", 9)
        sx(xq, y0); pdf.cell(C_QTE, 5, it["qte"], align="C")
        sx(xp, y0); pdf.cell(C_PU, 5, it["pu"] + " ", align="R")
        sx(xt, y0); pdf.cell(C_TOT, 5, it["tot"] + " ", align="R")
        pdf.set_font("Helvetica", "B", 9.5)
        sx(L + 2, y0)
        pdf.cell(C_DES - 2, 5, it["title"], new_x=XPos.LMARGIN,
                 new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 8.3); pdf.set_text_color(*GREY)
        sx(L + 2, pdf.get_y())
        pdf.multi_cell(C_DES - 2, 4.1, it["desc"], align="L",
                       new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        yend = pdf.get_y() + 2
        hr(yend, LINEC, 0.3)
        pdf.set_y(yend + 1)

    # ---- totaux
    pdf.set_text_color(*DARK)
    ytot = pdf.get_y() + 3
    xlab, LBL, VAL = 117, 50, 28

    def trow(lbl, val, fill=False, white=False, bold=False, h=7, size=9):
        y = pdf.get_y()
        if fill:
            pdf.set_fill_color(*NAVY)
        pdf.set_text_color(255, 255, 255) if white else pdf.set_text_color(*DARK)
        pdf.set_font("Helvetica", "B" if bold else "", size)
        sx(xlab, y); pdf.cell(LBL, h, lbl + "  ", align="L", fill=fill)
        sx(xlab + LBL, y); pdf.cell(VAL, h, val + " ", align="R", fill=fill,
                                    new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(ytot)
    trow("Total HT", cfg["total_ht"])
    trow(cfg["tva_label"], cfg["tva"])
    pdf.ln(0.5)
    trow("NET À PAYER (TTC)", cfg["ttc"], fill=True, white=True,
         bold=True, h=9, size=10.5)

    # ---- pied / mentions
    pdf.set_y(pdf.get_y() + 8)
    hr(pdf.get_y(), LINEC, 0.3)
    pdf.ln(2)

    def block(title, body):
        pdf.set_text_color(*NAVY); pdf.set_font("Helvetica", "B", 8.5)
        sx(L, pdf.get_y())
        pdf.cell(W, 5, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*GREY); pdf.set_font("Helvetica", "", 7.8)
        sx(L, pdf.get_y())
        pdf.multi_cell(W, 3.7, body, align="L", new_x=XPos.LMARGIN,
                       new_y=YPos.NEXT)
        pdf.ln(1.5)

    block("Conditions de règlement",
          f"Règlement par virement bancaire. Échéance : {cfg['echeance']} "
          "(30 jours à compter de la date de facture). Coordonnées "
          "bancaires communiquées séparément - compte professionnel en "
          "cours d'ouverture.")
    block("Mentions légales", cfg["mentions"])

    pdf.output(cfg["out"])
    print("OK ->", cfg["out"])


MENTIONS = (
    "Société JONCTION - SAS en cours de formation, au capital de 500 EUR, "
    "siège social 59 rue de Ponthieu 75008 Paris. Société en cours "
    "d'immatriculation au RCS de Paris - SIREN en cours d'attribution.\n"
    "Facture établie par M. Laurent FOURNIER, agissant au nom et pour le "
    "compte de la société JONCTION (SAS) en formation ; acte destiné à être "
    "repris par la société lors de son immatriculation.\n"
    "{tva}\n"
    "En cas de retard de paiement : pénalités de retard au taux de trois "
    "fois le taux d'intérêt légal, exigibles sans rappel, et indemnité "
    "forfaitaire pour frais de recouvrement de 40 EUR (art. L441-10 et "
    "D441-5 du Code de commerce). Aucun escompte pour paiement anticipé."
)
MENTION_TVA_FRANCHISE = "TVA non applicable, article 293 B du Code général des impôts."

HORAIRES = ("Horaires : 5 h/jour, du lundi au vendredi "
            "(8h30-11h00 / 14h00-16h30).")

juin = {
    "num": "2026-001", "date": "30/06/2026", "echeance": "30/07/2026",
    "periode": "   Période : du 19/06/2026 au 30/06/2026       "
               "Forfait mensuel 600 EUR HT - prorata 7/21 jours ouvrés",
    "items": [{
        "title": "Prestation d'assistanat commercial - Juin 2026",
        "desc": "Mise à disposition d'un assistant commercial basé à "
                "Madagascar.\n" + HORAIRES + "\n7 jours ouvrés travaillés "
                "(19 au 30/06, hors 26/06 - Indépendance malgache) sur 21 "
                "jours ouvrés de juin : prorata 7/21 du forfait.",
        "qte": "1", "pu": "200,00", "tot": "200,00"}],
    "total_ht": "200,00 EUR", "tva_label": "TVA (non applicable)",
    "tva": "0,00 EUR", "ttc": "200,00 EUR",
    "mentions": MENTIONS.format(tva=MENTION_TVA_FRANCHISE),
    "out": DIR + "Facture_2026-001_IL-DISTRIBUTION_juin.pdf",
}
juillet = {
    "num": "2026-002", "date": "31/07/2026", "echeance": "30/08/2026",
    "periode": "   Période : du 01/07/2026 au 31/07/2026       "
               "Forfait mensuel 600 EUR HT",
    "items": [{
        "title": "Prestation d'assistanat commercial - Juillet 2026",
        "desc": "Mise à disposition d'un assistant commercial basé à "
                "Madagascar.\n" + HORAIRES + "\nForfait mensuel complet : "
                "22 jours ouvrés (hors 14/07, fête nationale française).",
        "qte": "1", "pu": "600,00", "tot": "600,00"}],
    "total_ht": "600,00 EUR", "tva_label": "TVA (non applicable)",
    "tva": "0,00 EUR", "ttc": "600,00 EUR",
    "mentions": MENTIONS.format(tva=MENTION_TVA_FRANCHISE),
    "out": DIR + "Facture_2026-002_IL-DISTRIBUTION_juillet.pdf",
}

build(juin)
build(juillet)
