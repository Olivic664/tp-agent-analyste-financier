"""
=============================================================================
 TP SEMAINE 20 — Agent Analyste | export_pdf.py  (BONUS Niveau 3)
=============================================================================
 Rôle : transformer le rapport markdown produit par l'agent en un PDF
        propre et daté, comme le demande le bonus Niveau 3 du TP.

 Choix technique : ReportLab (bibliothèque PDF standard en Python).
 Le convertisseur reste volontairement SIMPLE : titres (#, ##), listes
 (- ), tableaux markdown basiques et paragraphes. L'objectif pédagogique
 est de montrer qu'un agent peut "agir sur le monde" en produisant un
 livrable de vraie qualité professionnelle.
=============================================================================
"""

import re
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _style(taille: int, gras: bool = False, couleur=None) -> ParagraphStyle:
    """Fabrique un style de paragraphe compact réutilisable."""
    return ParagraphStyle(
        f"style{taille}{gras}",
        fontSize=taille,
        leading=taille * 1.4,
        bold=gras,
        textColor=couleur or colors.HexColor("#1a1a2e"),
    )


def _markdown_vers_pdf(texte: str, chemin_pdf: Path) -> None:
    """Convertisseur markdown -> PDF minimal (titres, tableaux, listes)."""
    document = SimpleDocTemplate(
        str(chemin_pdf),
        pagesize=A4,
        title="Rapport financier — Agent Analyste (TP S20)",
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    corps = ParagraphStyle(
        "Corps", parent=styles["Normal"], fontSize=10, leading=14.5
    )
    puce = ParagraphStyle(
        "Puce", parent=corps, leftIndent=14, bulletIndent=4
    )

    elements = [
        Paragraph(
            f"Rapport financier — généré par l'Agent Analyste "
            f"(TP Semaine 20), le {date.today().strftime('%d/%m/%Y')}",
            _style(9, couleur=colors.HexColor("#555555")),
        ),
        Spacer(1, 10),
    ]

    lignes = texte.splitlines()
    i = 0
    while i < len(lignes):
        ligne = lignes[i]

        # Titres markdown (#, ##, ###)
        if ligne.startswith("### "):
            elements.append(
                Spacer(1, 6),
            )
            elements.append(Paragraph(ligne[4:], _style(12, gras=True)))
        elif ligne.startswith("## "):
            elements.append(Spacer(1, 10))
            elements.append(
                Paragraph(ligne[3:], _style(14, gras=True,
                                            couleur=colors.HexColor("#2E86AB")))
            )
        elif ligne.startswith("# "):
            elements.append(
                Paragraph(ligne[2:], _style(18, gras=True))
            )
        # Tableau markdown
        elif ligne.strip().startswith("|"):
            bloc_tableau = []
            while i < len(lignes) and lignes[i].strip().startswith("|"):
                cellules = [c.strip() for c in lignes[i].strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in cellules):  # ignore ---
                    bloc_tableau.append(cellules)
                i += 1
            if bloc_tableau:
                tableau = Table(bloc_tableau, hAlign="LEFT")
                tableau.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0),
                             colors.HexColor("#2E86AB")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("GRID", (0, 0), (-1, -1), 0.4,
                             colors.HexColor("#bbbbbb")),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                            ("TOPPADDING", (0, 0), (-1, -1), 3),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ]
                    )
                )
                elements.append(Spacer(1, 4))
                elements.append(tableau)
                elements.append(Spacer(1, 6))
            continue
        # Listes à puces
        elif re.match(r"^\s*[-*] ", ligne):
            elements.append(
                Paragraph(ligne.split(" ", 1)[1], puce, bulletText="•")
            )
        # Ligne vide = respiration
        elif not ligne.strip():
            elements.append(Spacer(1, 4))
        # Paragraphe normal
        else:
            # mise en gras markdown **...** -> <b>...</b>
            paragraphe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", ligne)
            elements.append(Paragraph(paragraphe, corps))
        i += 1

    document.build(elements)


def exporter_pdf(rapport_markdown: str, chemin_pdf: Path) -> None:
    """Point d'entrée : markdown de l'agent -> PDF daté."""
    _markdown_vers_pdf(rapport_markdown, Path(chemin_pdf))
