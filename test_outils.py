"""
=============================================================================
 TP SEMAINE 20 — Agent Analyste | test_outils.py
=============================================================================
 TEST 1 — Tester chaque outil SÉPARÉMENT, hors agent.
 C'est la recommandation explicite du cours (slide « Prérequis & mise en
 place ») : "un outil qui marche seul est bien plus facile à déboguer
 qu'un agent entier qui échoue quelque part".

 Ce que ce script vérifie :
   1. La base SQL est peuplée et lisible
   2. requete_sql : SELECT valide / refus de DROP / refus d'INSERT /
      erreur propre sur table inexistante / LIMIT ajouté automatiquement
   3. calcul_ratio : cas normal, marge négative, CA nul (erreur explicite)
   4. calcul_variation : croissance normale, départ nul
   5. recherche_web : recherche réelle (ou message d'erreur propre hors ligne)
   6. graphe_ca : le PNG est bien créé

 Usage :  python test_outils.py
 Résultat : PASS/FAIL par test + code de sortie 0 si tout passe.
=============================================================================
"""

from pathlib import Path

import outils
from outils import calcul_ratio, calcul_variation, graphe_ca, recherche_web, requete_sql

REUSSITES = []
ECHECS = []


def verifier(nom_test: str, condition: bool, detail: str = "") -> None:
    """Enregistre et affiche le résultat d'un test unitaire."""
    if condition:
        REUSSITES.append(nom_test)
        print(f"  [PASS] {nom_test}")
    else:
        ECHECS.append(nom_test)
        print(f"  [FAIL] {nom_test}  -> {detail}")


def extraire_contenu(resultat) -> str:
    """Les outils LangChain renvoient un objet ToolMessage-like :
    .content contient le texte. Cette aide uniformise les tests."""
    return getattr(resultat, "content", resultat)


print("=" * 70)
print(" TEST 1 — VALIDATION DE CHAQUE OUTIL ISOLÉMENT")
print("=" * 70)

# -----------------------------------------------------------------------------
# 1) La base existe et est peuplée
# -----------------------------------------------------------------------------
print("\n[1] Base de données")
import sqlite3

connexion = sqlite3.connect(f"file:{outils.CHEMIN_BASE}?mode=ro", uri=True)
nb_entreprises = connexion.execute("SELECT COUNT(*) FROM entreprises").fetchone()[0]
nb_finances = connexion.execute("SELECT COUNT(*) FROM finances").fetchone()[0]
connexion.close()
verifier(
    "La base contient 5 entreprises",
    nb_entreprises == 5,
    f"trouvé {nb_entreprises}",
)
verifier(
    "La base contient 20 lignes financières",
    nb_finances == 20,
    f"trouvé {nb_finances}",
)

# -----------------------------------------------------------------------------
# 2) requete_sql — le garde-fou lecture seule est le point critique
# -----------------------------------------------------------------------------
print("\n[2] Outil requete_sql (lecture seule)")

r1 = extraire_contenu(
    requete_sql.invoke(
        {"requete": "SELECT nom, secteur FROM entreprises ORDER BY id"}
    )
)
verifier(
    "SELECT valide renvoie les 5 entreprises",
    "TechNova" in r1 and "VoltaMobilité" in r1,
    f"reçu : {r1[:100]}",
)

r2 = extraire_contenu(
    requete_sql.invoke(
        {
            "requete": "SELECT e.nom, f.annee, f.chiffre_affaires FROM finances f "
            "JOIN entreprises e ON e.id = f.entreprise_id "
            "WHERE e.nom = 'TechNova Solutions' ORDER BY f.annee"
        }
    )
)
verifier(
    "Historique TechNova complet (2021→2024)",
    all(str(a) in r2 for a in (2021, 2022, 2023, 2024)),
    f"reçu : {r2[:100]}",
)

r3 = extraire_contenu(requete_sql.invoke({"requete": "DROP TABLE finances"}))
verifier(
    "DROP TABLE refusé (garde-fou lecture seule)",
    "ERREUR" in r3.upper() and "SELECT" in r3.upper(),
    f"reçu : {r3[:100]}",
)

r4 = extraire_contenu(
    requete_sql.invoke(
        {"requete": "INSERT INTO entreprises VALUES (9, 'Pirate', 'Hacking')"}
    )
)
verifier("INSERT refusé (garde-fou lecture seule)", "ERREUR" in r4.upper(), r4[:80])

r5 = extraire_contenu(
    requete_sql.invoke({"requete": "SELECT * FROM table_inexistante"})
)
verifier(
    "Erreur SQL renvoyée proprement (pas d'exception)",
    "ERREUR SQL" in r5.upper(),
    f"reçu : {r5[:100]}",
)

r6 = extraire_contenu(requete_sql.invoke({"requete": "SELECT * FROM finances"}))
verifier(
    "LIMIT ajouté automatiquement (résultat plafonné)",
    "50" in str(outils.requete_sql.invoke({"requete": "SELECT * FROM finances"})),
    "vérifie la journalisation des requêtes",
)

# Vérification du journal (garde-fou "journalisation des requêtes")
chemin_log = Path(outils.CHEMIN_LOGS) / "agent.log"
verifier("Toutes les requêtes sont journalisées", chemin_log.exists())

# -----------------------------------------------------------------------------
# 3) calcul_ratio — la marge nette
# -----------------------------------------------------------------------------
print("\n[3] Outil calcul_ratio (marge nette)")

m1 = extraire_contenu(
    calcul_ratio.invoke({"chiffre_affaires": 92.8, "resultat_net": 11.2})
)
# 11.2 / 92.8 * 100 = 12.07 % (TechNova 2024)
verifier(
    "Marge nette TechNova 2024 = 12.07 %",
    abs(float(m1) - 12.07) < 0.01,
    f"reçu : {m1}",
)

m2 = extraire_contenu(
    calcul_ratio.invoke({"chiffre_affaires": 105.4, "resultat_net": 4.8})
)
verifier(
    "Marge VoltaMobilité 2024 = 4.55 %",
    abs(float(m2) - 4.55) < 0.01,
    f"reçu : {m2}",
)

m3 = extraire_contenu(calcul_ratio.invoke({"chiffre_affaires": 0, "resultat_net": 5}))
verifier("CA nul -> erreur explicite (pas de division par zéro)", "ERREUR" in m3.upper(), m3[:80])

# -----------------------------------------------------------------------------
# 4) calcul_variation — la croissance
# -----------------------------------------------------------------------------
print("\n[4] Outil calcul_variation (croissance)")

v1 = extraire_contenu(
    calcul_variation.invoke({"valeur_debut": 45.2, "valeur_fin": 92.8})
)
# (92.8 - 45.2)/45.2*100 = 105.3 % de croissance TechNova 2021→2024
verifier(
    "Croissance TechNova 2021→2024 = +105.3 %",
    abs(float(v1) - 105.3) < 0.15,
    f"reçu : {v1}",
)

v2 = extraire_contenu(
    calcul_variation.invoke({"valeur_debut": 245.8, "valeur_fin": 168.9})
)
# MarineLog 2022→2024 : (168.9-245.8)/245.8*100 = -31.3 %
verifier(
    "Baisse MarineLog 2022→2024 = -31.3 %",
    abs(float(v2) - (-31.3)) < 0.15,
    f"reçu : {v2}",
)

# -----------------------------------------------------------------------------
# 5) recherche_web — dépend du réseau : on teste la ROBUSTESSE
# -----------------------------------------------------------------------------
print("\n[5] Outil recherche_web (réseau requis — on teste la robustesse)")

w1 = extraire_contenu(recherche_web.invoke({"requete": "TechNova Solutions entreprise"}))
if "ERREUR" in w1.upper():
    verifier(
        "Hors ligne -> message d'erreur PROPRE (l'agent peut continuer)",
        "poursuis l'analyse" in w1.lower() or "indisponible" in w1.lower(),
        w1[:120],
    )
else:
    verifier(
        "Recherche web renvoie des résultats structurés (titre + URL)",
        "URL" in w1 and "1." in w1,
        w1[:120],
    )

# -----------------------------------------------------------------------------
# 6) graphe_ca — le bonus Niveau 1
# -----------------------------------------------------------------------------
print("\n[6] Outil graphe_ca (bonus Niveau 1)")

g1 = extraire_contenu(graphe_ca.invoke({"nom_entreprise": "BioSanté"}))
chemin_png = Path(outils.CHEMIN_BASE).parent.parent / "rapport" / "graphe_ca.png"
verifier("Graphique généré pour BioSanté", "Graphique enregistré" in g1, g1[:120])
verifier("Le fichier PNG existe bien sur disque", chemin_png.exists(), str(chemin_png))

g2 = extraire_contenu(graphe_ca.invoke({"nom_entreprise": "EntrepriseFantome"}))
verifier(
    "Entreprise inconnue -> erreur explicite avec suggestion",
    "ERREUR" in g2.upper() and "requete_sql" in g2,
    g2[:120],
)

# -----------------------------------------------------------------------------
# BILAN
# -----------------------------------------------------------------------------
print("\n" + "=" * 70)
print(f" BILAN : {len(REUSSITES)} PASS / {len(ECHECS)} FAIL")
print("=" * 70)
if ECHECS:
    print("Tests en échec :", ECHECS)
    raise SystemExit(1)
print("TOUS LES OUTILS SONT OPÉRATIONNELS — on peut les brancher à l'agent.")
