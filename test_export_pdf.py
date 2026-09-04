"""
=============================================================================
 TP SEMAINE 20 — Agent Analyste | test_export_pdf.py
=============================================================================
 TEST 4 — Valider le BONUS Niveau 3 : l'export PDF du rapport.
 On fournit un rapport markdown typique (avec titres, tableau, listes,
 gras, sources) et on vérifie que le PDF est bien produit et non vide.
 Usage : python test_export_pdf.py
=============================================================================
"""

from pathlib import Path

from export_pdf import exporter_pdf

RAPPORT_EXEMPLE = """# RAPPORT FINANCIER — TechNova Solutions

## Résumé exécutif
TechNova Solutions (Technologie / Logiciel) affiche une croissance remarquable
du chiffre d'affaires : +105,3 % entre 2021 et 2024. La marge nette atteint
12,07 % en 2024, en nette progression.

## Chiffres clés (montants en millions d'euros)
| Année | CA | Résultat net | Marge nette | Dettes | Effectif |
|-------|-----|--------------|-------------|--------|----------|
| 2021  | 45.2 | 3.1 | 6.86 % | 12.0 | 210 |
| 2022  | 58.7 | 5.4 | 9.20 % | 14.5 | 260 |
| 2023  | 74.3 | 7.9 | 10.63 % | 15.2 | 310 |
| 2024  | 92.8 | 11.2 | 12.07 % | 16.0 | 355 |

## Analyse
- **Croissance** : le CA a plus que doublé en 4 ans (source : base SQL).
- **Rentabilité** : la marge nette progresse chaque année, signe d'un
  modèle qui gagne en efficacité (source : calcul_ratio).
- **Structure financière** : l'endettement reste modéré devant le CA.

## Risques
- Concentration de la croissance sur un secteur cyclique.
- Hausse rapide de l'effectif (+69 %) : pression sur les charges.

## Sources
- Base SQL finances (2021-2024), outil requete_sql
- Graphique rapport/graphe_ca.png, outil graphe_ca
"""

if __name__ == "__main__":
    print("=" * 70)
    print(" TEST 4 — EXPORT PDF DU RAPPORT (BONUS Niveau 3)")
    print("=" * 70)

    chemin = Path("rapport/test_rapport.pdf")
    exporter_pdf(RAPPORT_EXEMPLE, chemin)

    ok_existe = chemin.exists()
    taille = chemin.stat().st_size if ok_existe else 0
    # Un PDF valide commence par l'en-tête magique %PDF
    en_tete = chemin.read_bytes()[:5] if ok_existe else b""
    ok_pdf = en_tete == b"%PDF-"
    ok_taille = taille > 2000  # un vrai rapport fait plusieurs Ko

    print(f"  [{'PASS' if ok_existe else 'FAIL'}] Le fichier PDF existe")
    print(f"  [{'PASS' if ok_pdf else 'FAIL'}] En-tête PDF valide (%PDF-) : {en_tete}")
    print(f"  [{'PASS' if ok_taille else 'FAIL'}] Taille plausible ({taille} octets)")

    if ok_existe and ok_pdf and ok_taille:
        print(f"\n EXPORT PDF FONCTIONNEL : {chemin.resolve()}")
        raise SystemExit(0)
    raise SystemExit(1)
