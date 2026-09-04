"""
=============================================================================
 TP SEMAINE 20 — Agent Analyste | outils.py
=============================================================================
 Rôle de ce fichier (Étapes 1 & 2 du TP) :
   Définir les OUTILS de l'agent, c'est-à-dire ses "mains" : chaque outil
   enveloppe une action réelle (requête SQL, recherche web, calcul, graphe)
   que le LLM peut déclencher via le TOOL CALLING.

 Rappel du cours (Jour 2) :
   - Le LLM ne fait JAMAIS l'action lui-même : il produit un appel structuré
     (nom d'outil + arguments) ; c'est le code ci-dessous qui exécute vraiment.
   - La DESCRIPTION de chaque outil est le "mode d'emploi" que lit le modèle :
     une description précise => un choix d'outil fiable. On la rédige avec
     autant de soin qu'un prompt.
   - Sécurité : moindre privilège (SQL en LECTURE SEULE), erreurs explicites
     (l'agent peut se corriger au lieu de planter), résultats courts et
     structurés (économie de tokens).
=============================================================================
"""

import logging
import sqlite3
from pathlib import Path

from langchain_core.tools import tool

# -----------------------------------------------------------------------------
# Journalisation (garde-fou du cours : "journaliser chaque décision/requête")
# Tout ce que l'agent fait via ses outils est tracé dans logs/agent.log
# -----------------------------------------------------------------------------
CHEMIN_BASE = Path(__file__).resolve().parent / "data" / "finances.db"
CHEMIN_LOGS = Path(__file__).resolve().parent / "logs"
CHEMIN_LOGS.mkdir(exist_ok=True)

logging.basicConfig(
    filename=CHEMIN_LOGS / "agent.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
journal = logging.getLogger("agent_analyste")


# =============================================================================
# OUTIL 1 — requete_sql : interroger la base financière (LECTURE SEULE)
# =============================================================================
@tool
def requete_sql(requete: str) -> str:
    """Exécute une requête SQL SELECT en LECTURE SEULE sur la base financière
    SQLite de l'entreprise analysée.

    La base contient deux tables :
      - entreprises(id, nom, secteur)
      - finances(entreprise_id, annee, chiffre_affaires, resultat_net,
                 dettes_totales, effectif) — montants en MILLIONS d'euros,
                 années 2021 à 2024.

    Utilise cet outil pour récupérer les chiffres historiques d'une entreprise
    (CA, résultat net, dettes, effectif par année) avant tout calcul.

    Args:
        requete: une unique requête SQL commençant obligatoirement par SELECT.
    """
    requete_propre = requete.strip().rstrip(";")
    journal.info("SQL demandé : %s", requete_propre)

    # --- GARDE-FOU 1 : lecture seule --------------------------------------
    # On refuse tout verbe autre que SELECT (INSERT, UPDATE, DELETE, DROP...)
    premier_mot = requete_propre.split()[0].upper() if requete_propre else ""
    if premier_mot != "SELECT" and premier_mot != "WITH":
        message = (
            f"ERREUR DE SÉCURITÉ : seule la lecture (SELECT) est autorisée. "
            f"Requête refusée : « {requete_propre} ». "
            f"Reformule ta demande avec un SELECT."
        )
        journal.warning("SQL refusé (non-SELECT) : %s", requete_propre)
        return message  # Erreur EXPLICITE : l'agent peut se corriger

    # --- GARDE-FOU 2 : une seule instruction à la fois ---------------------
    if ";" in requete_propre:
        return (
            "ERREUR : une seule requête à la fois (pas de point-virgule "
            "interne). Simplifie ta requête."
        )

    # --- GARDE-FOU 3 : plafonner le volume renvoyé --------------------------
    # (règle du cours : renvoyer un résultat COURT et structuré)
    if "LIMIT" not in requete_propre.upper():
        requete_propre += " LIMIT 50"

    try:
        # mode=ro (read-only) : même côté SQLite, l'écriture est impossible.
        connexion = sqlite3.connect(f"file:{CHEMIN_BASE}?mode=ro", uri=True)
        curseur = connexion.execute(requete_propre)
        colonnes = [d[0] for d in curseur.description]
        lignes = curseur.fetchmany(50)
        connexion.close()
    except sqlite3.Error as erreur:
        journal.error("SQL en échec : %s | %s", requete_propre, erreur)
        return f"ERREUR SQL : {erreur}. Vérifie les noms de tables et colonnes."

    if not lignes:
        return "Résultat vide : aucune ligne ne correspond à cette requête."

    # Format lisible type tableau : l'agent relit ce texte pour raisonner.
    entete = " | ".join(colonnes)
    corps = "\n".join(
        " | ".join(str(v) for v in ligne) for ligne in lignes
    )
    resultat = f"{entete}\n{corps}"
    journal.info("SQL OK : %d ligne(s) renvoyée(s)", len(lignes))
    return resultat


# =============================================================================
# OUTIL 2 — recherche_web : ouvrir l'agent sur le monde (API externe)
# =============================================================================
@tool
def recherche_web(requete: str) -> str:
    """Recherche sur le web (DuckDuckGo) des informations récentes sur une
    entreprise : actualité, projets, chiffres publiés, rumeurs de marché.

    Utilise cet outil pour compléter l'analyse avec du contexte qualitatif à
    jour, que la base SQL ne contient pas. Renvoie les 5 meilleurs résultats
    (titre, url, extrait).

    Args:
        requete: la recherche en langage naturel, ex. « TechNova Solutions
                 actualité 2025 ».
    """
    journal.info("Recherche web : %s", requete)
    try:
        # import paresseux : le reste du TP fonctionne même sans connexion
        from ddgs import DDGS

        resultats_bruts = DDGS().text(requete, max_results=5)
    except Exception as erreur:  # réseau indisponible, rate-limit, etc.
        journal.error("Recherche web en échec : %s", erreur)
        return (
            "ERREUR : la recherche web est indisponible pour le moment "
            f"({erreur}). Poursuis l'analyse avec la base SQL et signale "
            "dans le rapport que le contexte web n'a pas pu être vérifié."
        )

    if not resultats_bruts:
        return "Aucun résultat web trouvé pour cette recherche."

    # Format court et structuré (une ligne par résultat = économie de tokens)
    lignes = []
    for i, r in enumerate(resultats_bruts, start=1):
        titre = r.get("title") or r.get("titre") or "(sans titre)"
        url = r.get("url") or r.get("href") or r.get("link") or ""
        extrait = r.get("description") or r.get("body") or r.get("snippet") or ""
        lignes.append(f"{i}. {titre}\n   URL : {url}\n   {extrait[:300]}")

    journal.info("Recherche web OK : %d résultat(s)", len(lignes))
    return "\n\n".join(lignes)


# =============================================================================
# OUTIL 3 — calcul_ratio : la marge nette (calcul fiable, pas "de tête")
# =============================================================================
@tool
def calcul_ratio(chiffre_affaires: float, resultat_net: float) -> float:
    """Calcule la MARGE NETTE en pourcentage : (résultat net / chiffre
    d'affaires) × 100.

    Utilise cet outil pour mesurer la rentabilité d'une entreprise à partir
    des chiffres extraits de la base SQL, au lieu de calculer mentalement.

    Args:
        chiffre_affaires: CA de l'année, en millions d'euros.
        resultat_net: résultat net de la même année, en millions d'euros
                      (peut être négatif).
    """
    journal.info(
        "Calcul marge nette : CA=%s, RN=%s", chiffre_affaires, resultat_net
    )
    if chiffre_affaires == 0:
        # Erreur explicite : le message indique quoi faire
        return "ERREUR : le chiffre d'affaires est nul, marge incalculable."
    marge = round(resultat_net / chiffre_affaires * 100, 2)
    return marge


# =============================================================================
# OUTIL 4 — calcul_variation : la croissance entre deux années
# =============================================================================
@tool
def calcul_variation(valeur_debut: float, valeur_fin: float) -> float:
    """Calcule la VARIATION EN POURCENTAGE entre deux valeurs :
    (valeur_fin - valeur_debut) / valeur_debut × 100.

    Utilise cet outil pour exprimer la croissance (ou la baisse) du CA, du
    résultat ou des dettes entre deux années consécutives.

    Args:
        valeur_debut: valeur de l'année de départ (ex. CA 2021).
        valeur_fin: valeur de l'année d'arrivée (ex. CA 2024).
    """
    journal.info(
        "Calcul variation : %s -> %s", valeur_debut, valeur_fin
    )
    if valeur_debut == 0:
        return "ERREUR : valeur de départ nulle, variation incalculable."
    variation = round((valeur_fin - valeur_debut) / abs(valeur_debut) * 100, 1)
    return variation


# =============================================================================
# OUTIL 5 (BONUS Niveau 1) — graphe_ca : tracer l'évolution du CA
# =============================================================================
@tool
def graphe_ca(nom_entreprise: str) -> str:
    """Génère un graphique en barres de l'évolution du chiffre d'affaires
    d'une entreprise (toutes les années disponibles dans la base) et
    l'enregistre en PNG dans le dossier rapport/.

    Utilise cet outil avant de rédiger le rapport pour joindre une
    illustration visuelle de la dynamique commerciale.

    Args:
        nom_entreprise: le nom exact (ou partiel) de l'entreprise, tel qu'il
                        figure dans la table entreprises.
    """
    journal.info("Graphe CA demandé pour : %s", nom_entreprise)

    # Lecture directe de la base (lecture seule) — pas besoin du LLM ici
    try:
        connexion = sqlite3.connect(f"file:{CHEMIN_BASE}?mode=ro", uri=True)
        lignes = connexion.execute(
            """SELECT f.annee, f.chiffre_affaires
               FROM finances f
               JOIN entreprises e ON e.id = f.entreprise_id
               WHERE e.nom LIKE ? ORDER BY f.annee""",
            (f"%{nom_entreprise}%",),
        ).fetchall()
        connexion.close()
    except sqlite3.Error as erreur:
        return f"ERREUR SQL lors du graphe : {erreur}"

    if not lignes:
        return (
            f"ERREUR : aucune entreprise ne correspond à "
            f"« {nom_entreprise} » dans la base. Vérifie l'orthographe "
            f"(outil requete_sql : SELECT nom FROM entreprises)."
        )

    annees = [str(l[0]) for l in lignes]
    cas = [l[1] for l in lignes]
    nom_trouve = nom_entreprise  # simplification affichée dans le titre

    # --- Tracé matplotlib (matplotlib gère seul la mise en page) -----------
    import matplotlib

    matplotlib.use("Agg")  # rendu sans écran (serveur / script)
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4), constrained_layout=True)
    barres = ax.bar(annees, cas, color="#2E86AB", edgecolor="white")
    ax.bar_label(barres, fmt="%.1f", padding=2, fontsize=9)
    ax.set_title(f"Évolution du chiffre d'affaires — {nom_trouve}")
    ax.set_xlabel("Année")
    ax.set_ylabel("CA (millions d'euros)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3)

    chemin_png = Path(__file__).resolve().parent / "rapport" / "graphe_ca.png"
    chemin_png.parent.mkdir(exist_ok=True)
    fig.savefig(chemin_png, dpi=150)
    plt.close(fig)

    journal.info("Graphe généré : %s", chemin_png)
    return (
        f"Graphique enregistré : {chemin_png.name} "
        f"(dossier rapport/). Données tracées — "
        f"CA par année : {', '.join(f'{a}: {c} M€' for a, c in zip(annees, cas))}."
    )


# =============================================================================
# ÉTAPE 2 DU TP — La boîte à outils regroupée
# =============================================================================
BOITE_A_OUTILS = [
    requete_sql,
    recherche_web,
    calcul_ratio,
    calcul_variation,
    graphe_ca,
]
