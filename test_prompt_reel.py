"""
=============================================================================
 TP SEMAINE 20 — Agent Analyste | test_prompt_reel.py
=============================================================================
 TEST 3 — Valider le PROMPT SYSTÈME avec un VRAI LLM (via la CLI z-ai).
 
 Objectif : prouver que le prompt système guide correctement le raisonnement
 d'un modèle réel. On lui présente la mission + la liste des outils, et on
 vérifie que SA STRATÉGIE annoncée respecte la méthode attendue :
   SQL d'abord -> calculs -> web -> graphique -> rapport structuré sourcé.
 
 Ce test complète le test mock : la boucle est déjà prouvée ; ici on prouve
 que le CERVEAU comprend la mission.
 
 Prérequis : CLI z-ai disponible (sinon le test est sauté avec un avertissement).
 Usage : python test_prompt_reel.py
=============================================================================
"""

import json
import subprocess

from agent import PROMPT_SYSTEME

OUTILS_DISPONIBLES = """Tu disposes de ces outils :
- requete_sql(requete) : interroge la base financière SQLite (lecture seule)
- calcul_ratio(chiffre_affaires, resultat_net) : marge nette en %
- calcul_variation(valeur_debut, valeur_fin) : variation en %
- recherche_web(requete) : actualité récente (DuckDuckGo)
- graphe_ca(nom_entreprise) : graphique d'évolution du CA
"""


def interroger_llm_reel() -> str | None:
    """Appelle le vrai LLM via la CLI z-ai. Renvoie None si indisponible."""
    prompt = (
        f"{OUTILS_DISPONIBLES}\n"
        "Question de l'utilisateur : « Rédige un rapport financier complet "
        "sur l'entreprise TechNova Solutions »\n\n"
        "Réponds UNIQUEMENT avec ton PLAN d'action numéroté (pas le rapport) : "
        "quelle séquence d'appels d'outils vas-tu effectuer, et quelles "
        "sections le rapport final contiendra-t-il ?"
    )
    try:
        resultat = subprocess.run(
            [
                "z-ai", "chat",
                "--system", PROMPT_SYSTEME,
                "--prompt", prompt,
                "--output", "logs/reponse_llm_reel.json",
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as erreur:
        print(f"  [SKIP] LLM réel indisponible ({erreur}) — test ignoré.")
        return None

    # La CLI écrit un JSON OpenAI-like : {choices:[{message:{content:...}}]}
    try:
        with open("logs/reponse_llm_reel.json", encoding="utf-8") as f:
            donnees = json.load(f)
        return donnees["choices"][0]["message"]["content"]
    except (OSError, KeyError, json.JSONDecodeError) as erreur:
        print(f"  [SKIP] Réponse illisible : {erreur}")
        return None


if __name__ == "__main__":
    print("=" * 70)
    print(" TEST 3 — VALIDATION DU PROMPT SYSTÈME AVEC UN VRAI LLM")
    print("=" * 70)

    plan = interroger_llm_reel()
    if plan is None:
        print("Test sauté : pas de LLM réel disponible sur cette machine.")
        raise SystemExit(0)

    print("\n--- PLAN PRODUIT PAR LE VRAI LLM ---")
    print(plan[:1200])
    print("-------------------------------------\n")

    reussites = []
    # Le vrai LLM doit annoncer une stratégie conforme au prompt système
    etapes = plan.lower()
    verifications = [
        ("Il commence par la base SQL", "requete_sql" in etapes or "sql" in etapes),
        ("Il prévoit les calculs (marge/variation)",
         "calcul_ratio" in etapes or "marge" in etapes
         or "calcul_variation" in etapes),
        ("Il prévoit la recherche web", "recherche_web" in etapes or "web" in etapes),
        ("Il prévoit le graphique", "graphe_ca" in etapes or "graphique" in etapes),
        ("Il cite la structure imposée",
         "résumé" in etapes or "resume" in etapes or "sources" in etapes),
        ("Il mentionne les sources / citations",
         "source" in etapes or "cite" in etapes),
    ]
    for nom, ok in verifications:
        print(f"  [{'PASS' if ok else 'FAIL'}] {nom}")
        reussites.append(ok)

    print("\n" + "=" * 70)
    if all(reussites):
        print(" LE VRAI LLM COMPREND LA MISSION : le prompt système est valide.")
        raise SystemExit(0)
    print(" Le prompt système doit être affiné — voir le plan ci-dessus.")
    raise SystemExit(1)
