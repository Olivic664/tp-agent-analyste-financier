"""
=============================================================================
 TP SEMAINE 20 — Agent Analyste | run.py
=============================================================================
 Rôle de ce fichier (Étape 5 du TP) :
   Le point d'entrée "utilisateur" : on donne le nom d'une entreprise,
   l'agent boucle tout seul (planifier -> outil -> observer -> ... ) et
   renvoie le rapport financier final.

 Usage :
   python run.py "TechNova Solutions"                 # rapport markdown
   python run.py "VoltaMobilité" --pdf                # + export PDF (bonus)
   python run.py "MarineLog Shipping" --model gpt-4o  # modèle explicite

 Prérequis :
   - La clé d'API dans un fichier .env : OPENAI_API_KEY=sk-...
   - pip install -r requirements.txt
=============================================================================
"""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from agent import MAX_ETAPES, construire_agent, lancer_analyse

# Chargement du .env (clé d'API) — jamais de clé en dur dans le code !
load_dotenv(Path(__file__).resolve().parent / ".env")


def principal() -> int:
    parseur = argparse.ArgumentParser(
        description="Agent Analyste — rapport financier autonome (TP S20)"
    )
    parseur.add_argument("entreprise", help="Nom de l'entreprise à analyser")
    parseur.add_argument(
        "--model", default="gpt-4o", help="Modèle OpenAI (défaut : gpt-4o)"
    )
    parseur.add_argument(
        "--pdf",
        action="store_true",
        help="Exporte aussi le rapport en PDF (bonus Niveau 3)",
    )
    args = parseur.parse_args()

    print("=" * 70)
    print(" AGENT ANALYSTE — TP Semaine 20 (LangGraph)")
    print("=" * 70)
    print(f"Entreprise : {args.entreprise}")
    print(f"Modèle     : {args.model}")
    print(f"Limite     : {MAX_ETAPES} étapes max (garde-fou anti-boucle)")
    print("-" * 70)

    # --- Construction et lancement de l'agent -----------------------------
    agent = construire_agent(model=args.model)
    objectif = (
        f"Rédige un rapport financier complet sur l'entreprise "
        f"« {args.entreprise} ». Utilise la base SQL, les calculs, la "
        f"recherche web et le graphique avant de rédiger."
    )

    print("\nL'agent travaille (boucle ReAct en cours)...\n")
    try:
        # stream() affiche chaque tour de boucle EN DIRECT : c'est
        # l'observabilité minimale recommandée par le cours (Jour 3).
        for evenement in agent.stream(
            {"messages": [("user", objectif)]},
            config={
                "configurable": {"thread_id": f"analyse-{args.entreprise}"},
                "recursion_limit": MAX_ETAPES,
            },
            stream_mode="updates",
        ):
            for nom_noeud, mise_a_jour in evenement.items():
                derniers = mise_a_jour.get("messages", [])
                for message in derniers:
                    type_message = type(message).__name__
                    contenu = str(getattr(message, "content", ""))[:120]
                    appels = getattr(message, "tool_calls", None)
                    if appels:
                        for appel in appels:
                            print(
                                f"  [agent] appelle {appel['name']} "
                                f"({appel['args']})"
                            )
                    elif nom_noeud == "outils":
                        print(f"  [outil] {contenu[:100]}...")
                    else:
                        print(f"  [{nom_noeud}/{type_message}] {contenu}")
        print("\n" + "-" * 70)

        # L'état final : le dernier message contient le rapport
        etat_final = agent.get_state(
            config={"configurable": {"thread_id": f"analyse-{args.entreprise}"}}
        )
        rapport = etat_final.values["messages"][-1].content

    except KeyboardInterrupt:
        print("\nInterrompu par l'utilisateur.")
        return 130
    except Exception as erreur:
        # Garde-fou : une GraphRecursionError arrive ici, proprement.
        print(f"\nARRÊT DE SÉCURITÉ : {type(erreur).__name__}")
        print(f"Détail : {erreur}")
        print(
            "L'agent a dépassé la limite d'étapes ou rencontré une erreur "
            "irrécupérable — consulte logs/agent.log pour le diagnostic."
        )
        return 1

    # --- Sauvegarde du rapport en markdown --------------------------------
    dossier_rapport = Path(__file__).resolve().parent / "rapport"
    dossier_rapport.mkdir(exist_ok=True)
    slug = (
        args.entreprise.lower()
        .replace(" ", "_")
        .replace("'", "")
        .replace("é", "e").replace("è", "e").replace("à", "a")
    )
    chemin_md = dossier_rapport / f"rapport_{slug}.md"
    chemin_md.write_text(rapport, encoding="utf-8")
    print(f"Rapport markdown enregistré : {chemin_md}")

    # --- Bonus Niveau 3 : export PDF --------------------------------------
    if args.pdf:
        from export_pdf import exporter_pdf

        chemin_pdf = dossier_rapport / f"rapport_{slug}.pdf"
        exporter_pdf(rapport, chemin_pdf)
        print(f"Rapport PDF enregistré      : {chemin_pdf}")

    # Aperçu dans la console
    print("\n" + "=" * 70)
    print(" RAPPORT GÉNÉRÉ")
    print("=" * 70)
    print(rapport)
    return 0


if __name__ == "__main__":
    sys.exit(principal())
