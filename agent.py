"""
=============================================================================
 TP SEMAINE 20 — Agent Analyste | agent.py
=============================================================================
 Rôle de ce fichier (Étapes 3, 4, 6 et 7 du TP) :
   Construire le GRAPHE LangGraph qui transforme un simple LLM en agent
   autonome : boucle agent <-> outils, mémoire persistante, prompt système
   qui cadre le rapport, et garde-fous.

 Les trois choix structurants (à pouvoir justifier à l'oral) :
   1. LangGraph est choisi (vs CrewAI/AutoGen) car un flux d'analyse
      financière est TRÈS STRUCTURÉ : il faut un contrôle fin, des
      conditions, des cycles maîtrisés (tableau de décision du Jour 3).
   2. La boucle est le motif ReAct : réfléchir -> agir (outil) -> observer ->
      décider de continuer ou conclure. C'est l'arête retour "outils -> agent"
      qui crée l'autonomie.
   3. Les garde-fous (limite d'étapes via recursion_limit, SQL lecture seule,
      sources obligatoires dans le prompt) encadrent l'autonomie : le cours
      insiste — "la puissance vient de l'autonomie ; la fiabilité vient des
      garde-fous".
=============================================================================
"""

from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from outils import BOITE_A_OUTILS

# LLM injecté par construire_agent (évite de le passer de nœud en nœud)
_llm = None

# -----------------------------------------------------------------------------
# GARDE-FOU 1 (Étape 7) : nombre MAXIMUM de tours de boucle.
# Chaque tour = un appel LLM facturé + un risque de dérive. Au-delà de cette
# limite, LangGraph lève une erreur : on coupe plutôt que de tourner en rond.
# -----------------------------------------------------------------------------
MAX_ETAPES = 25


# =============================================================================
# ÉTAT DU GRAPHE — la "mémoire de travail" partagée par tous les nœuds
# =============================================================================
class EtatAgent(TypedDict):
    """État partagé du graphe.

    `messages` contient TOUT l'historique : consigne, réflexions de l'agent,
    appels d'outils, résultats observés. add_messages concatène chaque
    nouvelle liste à l'historique existant : c'est ce qui donne à l'agent
    sa mémoire à chaque tour de boucle.
    """

    messages: Annotated[list[BaseMessage], add_messages]



# =============================================================================
# ÉTAPE 6 — LE PROMPT SYSTÈME : cadrer la mission ET le rapport
# =============================================================================
PROMPT_SYSTEME = (
    "Tu es un analyste financier senior. Ta mission : rédiger un rapport "
    "financier complet sur l'entreprise que l'utilisateur te donne.\n\n"
    "MÉTHODE (suis ces étapes dans l'ordre) :\n"
    "1. Récupère l'historique financier complet de l'entreprise avec l'outil "
    "requete_sql (tables : entreprises, finances — montants en millions d'euros).\n"
    "2. Calcule la marge nette avec calcul_ratio et les évolutions avec "
    "calcul_variation (ne fais JAMAIS ces calculs de tête).\n"
    "3. Cherche l'actualité récente avec recherche_web (si l'outil échoue, "
    "continue et signale-le dans les limites de l'analyse).\n"
    "4. Génère le graphique d'évolution du CA avec graphe_ca.\n"
    "5. Rédige le rapport final en markdown.\n\n"
    "STRUCTURE OBLIGATOIRE DU RAPPORT :\n"
    "## Résumé exécutif (5 lignes max)\n"
    "## Chiffres clés (tableau markdown des 4 dernières années)\n"
    "## Analyse (croissance du CA, rentabilité, structure financière)\n"
    "## Risques (points de vigilance concrets)\n"
    "## Sources (liste précise : requêtes SQL ou URLs utilisées)\n\n"
    "RÈGLES ABSOLUES :\n"
    "- Cite la SOURCE de chaque chiffre (table SQL ou URL du web).\n"
    "- Si une donnée manque, signale-le explicitement au lieu d'inventer.\n"
    "- Les montants de la base sont en millions d'euros : dis-le dans le rapport."
)


# =============================================================================
# NŒUD 1 — "agent" : le LLM réfléchit et décide
# =============================================================================
def noeud_agent(etat: EtatAgent) -> dict:
    """Appelle le LLM avec tout l'historique.

    Deux issues possibles (le LLM décide tout seul) :
      - il renvoie un tool_call => on ira au nœud "outils" ;
      - il renvoie du texte final => le graphe se termine.
    """
    # Le premier message de la conversation est notre consigne utilisateur ;
    # on préfixe toujours le prompt système pour cadrer le comportement.
    messages_avec_systeme = [("system", PROMPT_SYSTEME)] + etat["messages"]
    reponse = _llm.invoke(messages_avec_systeme)
    return {"messages": [reponse]}


# =============================================================================
# ARÊTE CONDITIONNELLE — "faut-il un outil ?" (le cœur de la boucle ReAct)
# =============================================================================
def faut_il_un_outil(etat: EtatAgent) -> str:
    """Lit la DERNIÈRE réponse du LLM et route le graphe.

    - Si le message contient des tool_calls -> il veut AGIR -> nœud "outils".
    - Sinon -> il a CONCLU (texte final) -> END.
    C'est exactement le "décide : continuer ou conclure" du schéma du cours.
    """
    dernier_message: AIMessage = etat["messages"][-1]
    if getattr(dernier_message, "tool_calls", None):
        return "outil"
    return "fin"


# =============================================================================
# NŒUD 2 — "outils" : l'exécuteur (ToolNode de LangGraph)
# =============================================================================
# ToolNode exécute chaque tool_call demandé par le LLM et renvoie les
# résultats sous forme de messages "tool" ajoutés à l'historique.
NOEUD_OUTILS = ToolNode(BOITE_A_OUTILS)


# =============================================================================
# ÉTAPES 3, 4, 5 — Construction du graphe, compilation avec mémoire
# =============================================================================
def construire_agent(model: str = "gpt-4o", temperature: float = 0.0, llm=None):
    """Assemble le graphe complet et le compile avec sa mémoire.

    Args:
        model: nom du modèle OpenAI (le cours utilise gpt-4o).
        temperature: 0.0 = réponses déterministes, indispensable en analyse
                     financière (même question => même démarche).
        llm: INJECTION DE DÉPENDANCE (optionnel) — permet de brancher un LLM
             de test (LLM fictif) sans clé API. En production, on laisse
             None : un ChatOpenAI est créé automatiquement.

    Returns:
        Le graphe compilé, prêt à être invoqué (app.invoke / app.stream).
    """
    global _llm

    # --- ÉTAPE 3 : le LLM, avec ses outils ---------------------------------
    # bind_tools annonce la boîte à outils au modèle : c'est ce qui lui permet
    # d'ÉMETTRE des appels structurés (nom d'outil + arguments) au format JSON.
    if llm is None:
        llm = ChatOpenAI(model=model, temperature=temperature)
    _llm = llm.bind_tools(BOITE_A_OUTILS)

    # --- ÉTAPE 4 : description du graphe (boucle agent <-> outils) ---------
    graphe = StateGraph(EtatAgent)
    graphe.add_node("agent", noeud_agent)
    graphe.add_node("outils", NOEUD_OUTILS)

    graphe.add_edge(START, "agent")  # entrée : on commence par réfléchir
    graphe.add_conditional_edges(
        "agent",
        faut_il_un_outil,          # la fonction de routage
        {"outil": "outils", "fin": END},
    )
    graphe.add_edge("outils", "agent")  # LA BOUCLE : l'agent relit le résultat

    # --- ÉTAPE 5 : compilation avec mémoire (MemorySaver) ------------------
    # checkpointer = mémoire de travail persistante entre les invocations
    # d'un même "thread" : on peut poser des questions de suivi sans tout
    # repartir de zéro (thread_id = identifiant de la mission).
    return graphe.compile(checkpointer=MemorySaver())


def lancer_analyse(graphe_compile, objectif: str, thread_id: str = "analyse") -> dict:
    """Exécute la mission complète et renvoie l'état final.

    GARDE-FOU 1 : `recursion_limit` borne le nombre d'étapes de la boucle
    (protection anti-boucle-infinie). En cas de dépassement, LangGraph lève
    une GraphRecursionError que run.py affiche proprement.
    """
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": MAX_ETAPES,
    }
    return graphe_compile.invoke(
        {"messages": [("user", objectif)]}, config
    )
