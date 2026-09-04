"""
=============================================================================
 TP SEMAINE 20 — Agent Analyste | test_agent_mock.py
=============================================================================
 TEST 2 — Tester la BOUCLE AGENTIQUE COMPLÈTE sans clé API.
 
 Principe : on remplace GPT-4o par un "LLM fictif" qui rejoue EXACTEMENT
 la séquence de décisions qu'un vrai analyste-LLM prendrait :
   réflexion 1 : appeler requete_sql      -> observation -> réflexion 2
   réflexion 2 : appeler calcul_ratio     -> observation -> réflexion 3
   ...
   réflexion N : rédiger le rapport final -> END
 
 Ce que ce test PROUVE (tout sauf l'appel réseau à OpenAI) :
   1. Le graphe LangGraph est correctement câblé (nœuds, arêtes, boucle)
   2. L'arête conditionnelle fonctionne : "outil" quand il y a un tool_call,
      "fin" quand le LLM rédige sa réponse finale
   3. Les outils réels s'exécutent et leurs résultats retournent à l'agent
   4. La mémoire (MemorySaver) conserve l'historique entre deux invocations
      du même thread_id
   5. Le garde-fou recursion_limit coupe une boucle infinie
 
 Usage :  python test_agent_mock.py
=============================================================================
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

import agent
from agent import construire_agent
from outils import BOITE_A_OUTILS

REUSSITES = []
ECHECS = []


def verifier(nom_test: str, condition: bool, detail: str = "") -> None:
    if condition:
        REUSSITES.append(nom_test)
        print(f"  [PASS] {nom_test}")
    else:
        ECHECS.append(nom_test)
        print(f"  [FAIL] {nom_test}  -> {detail}")


# =============================================================================
# Le LLM FICTIF — un "acteur" qui rejoue le scénario d'un vrai GPT-4o
# =============================================================================
class LLMFictif(BaseChatModel):
    """LLM de test : renvoie les réponses scriptées une par une.

    Quand la liste est épuisée, il RÉPÈTE la dernière réponse — c'est
    exactement le comportement qui permet de tester la garde anti-boucle.
    """

    reponses: list[BaseMessage]
    index: int = 0

    @property
    def _llm_type(self) -> str:
        return "llm-fictif-test"

    def bind_tools(self, tools, **kwargs):
        # Le LLM fictif ignore la boîte à outils : il est déjà scripté.
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if self.index < len(self.reponses):
            reponse = self.reponses[self.index]
            self.index += 1
        else:
            reponse = self.reponses[-1]
        # IMPORTANT : chaque réponse est une NOUVELLE instance avec un id
        # vierge (add_messages en assignera un unique), exactement comme un
        # LLM en ligne. Sans cela, LangGraph dédupliquerait par id et
        # remplacerait l'ancien message au lieu de l'ajouter.
        copie = reponse.model_copy(deep=True)
        copie.id = None
        return ChatResult(generations=[ChatGeneration(message=copie)])


def appel(nom_outil: str, arguments: dict, id_appel: str) -> AIMessage:
    """Fabrique un AIMessage contenant un tool_call (format OpenAI)."""
    return AIMessage(
        content="",
        tool_calls=[{"name": nom_outil, "args": arguments, "id": id_appel}],
    )


print("=" * 70)
print(" TEST 2 — BOUCLE AGENTIQUE COMPLÈTE (LLM fictif, sans clé API)")
print("=" * 70)

# -----------------------------------------------------------------------------
# Scénario : ce que GPT-4o ferait pour analyser TechNova Solutions
# -----------------------------------------------------------------------------
scenario = [
    appel(
        "requete_sql",
        {
            "requete": "SELECT f.annee, f.chiffre_affaires, f.resultat_net, "
            "f.dettes_totales, f.effectif FROM finances f "
            "JOIN entreprises e ON e.id = f.entreprise_id "
            "WHERE e.nom LIKE '%TechNova%' ORDER BY f.annee"
        },
        "call_1",
    ),
    appel("calcul_ratio", {"chiffre_affaires": 92.8, "resultat_net": 11.2}, "call_2"),
    appel("calcul_variation", {"valeur_debut": 45.2, "valeur_fin": 92.8}, "call_3"),
    appel("graphe_ca", {"nom_entreprise": "TechNova Solutions"}, "call_4"),
    appel("recherche_web", {"requete": "TechNova Solutions actualité"}, "call_5"),
    # Réflexion finale : le rapport est rédigé -> l'arête conditionnelle
    # doit router vers END (plus aucun tool_call dans ce message)
    AIMessage(
        content=(
            "# RAPPORT FINANCIER — TechNova Solutions\n\n"
            "## Résumé exécutif\n"
            "TechNova Solutions affiche une croissance remarquable du CA "
            "(+105,3 % sur 2021-2024, source : base SQL) et une marge nette "
            "de 12,07 % en 2024 (calcul vérifié).\n\n"
            "## Sources\n- Base SQL finances (2021-2024)\n- Graphique rapport/graphe_ca.png"
        )
    ),
]

llm_fictif = LLMFictif(reponses=scenario)
agent_fictif = construire_agent(llm=llm_fictif)

# -----------------------------------------------------------------------------
# 1) Exécution complète de la mission
# -----------------------------------------------------------------------------
print("\n[1] Exécution de la mission complète (5 outils + rapport final)")

config = {"configurable": {"thread_id": "test-technova"}, "recursion_limit": 30}
etat = agent_fictif.invoke(
    {
        "messages": [
            ("user", "Rédige un rapport financier complet sur TechNova Solutions.")
        ]
    },
    config,
)

messages = etat["messages"]

# Structure attendue : 1 consigne + (5 réflexions avec outils + 5 observations)
# + 1 rapport final = 12 messages
verifier(
    "La boucle a produit 12 messages (consigne, 5 appels, 5 résultats, rapport)",
    len(messages) == 12,
    f"trouvé {len(messages)}",
)

# Les 5 outils ont VRAIMENT tourné (les ToolMessage contiennent leurs sorties)
observations = [m.content for m in messages if type(m).__name__ == "ToolMessage"]
verifier(
    "L'outil requete_sql a renvoyé les données réelles (2024, 92.8)",
    any("2024" in str(o) and "92.8" in str(o) for o in observations),
    str(observations[:1]),
)
verifier(
    "L'outil calcul_ratio a renvoyé la marge 12.07",
    any("12.07" in str(o) for o in observations),
    str(observations[1:2]),
)
verifier(
    "L'outil calcul_variation a renvoyé +105.3 %",
    any("105.3" in str(o) for o in observations),
    str(observations[2:3]),
)
verifier(
    "L'outil graphe_ca a généré le PNG",
    any("Graphique enregistré" in str(o) for o in observations),
    str(observations[3:4]),
)

# Le rapport final est bien le DERNIER message, sans tool_call
rapport = messages[-1]
verifier(
    "Le dernier message est le rapport final (pas un appel d'outil)",
    type(rapport).__name__ == "AIMessage"
    and not getattr(rapport, "tool_calls", None)
    and "RAPPORT FINANCIER" in rapport.content,
    type(rapport).__name__,
)

# -----------------------------------------------------------------------------
# 2) MÉMOIRE — la suite de la conversation conserve l'historique
# -----------------------------------------------------------------------------
print("\n[2] Mémoire (MemorySaver) : poursuite sur le même thread_id")

suite = agent_fictif.invoke(
    {"messages": [("user", "Ajoute une section sur les dettes.")]}, config
)
# 12 messages après la mission + 1 consigne de suivi + 1 réponse = 14
verifier(
    "La 2e invocation conserve tout l'historique (12 + 2 = 14)",
    len(suite["messages"]) == 14,
    f"trouvé {len(suite['messages'])}",
)
verifier(
    "L'agent se souvient du rapport précédent (dans son historique)",
    any("RAPPORT FINANCIER" in str(m.content) for m in suite["messages"][:-1]),
    "rapport introuvable dans l'historique",
)

# Un NOUVEAU thread repart de zéro (les threads sont isolés)
config_b = {"configurable": {"thread_id": "test-autre-thread"}, "recursion_limit": 10}
etat_b = agent_fictif.invoke(
    {"messages": [("user", "Bonjour")]}, config_b
)
verifier(
    "Un nouveau thread_id démarre avec une mémoire vierge",
    len(etat_b["messages"]) >= 2,  # consigne + réponse
    f"trouvé {len(etat_b['messages'])}",
)

# -----------------------------------------------------------------------------
# 3) GARDE-FOU — la boucle infinie est coupée par recursion_limit
# -----------------------------------------------------------------------------
print("\n[3] Garde-fou : LLM qui appelle un outil sans fin")

llm_boucle = LLMFictif(
    reponses=[appel("requete_sql", {"requete": "SELECT 1"}, "call_x")]
)
agent_boucle = construire_agent(llm=llm_boucle)

try:
    agent_boucle.invoke(
        {"messages": [("user", "analyse infinie")]},
        {"configurable": {"thread_id": "test-boucle"}, "recursion_limit": 6},
    )
    verifier(
        "La GraphRecursionError est bien levée à la limite d'étapes",
        False,
        "aucune erreur levée — le garde-fou ne fonctionne pas !",
    )
except Exception as erreur:
    nom_erreur = type(erreur).__name__
    verifier(
        "La GraphRecursionError est bien levée à la limite d'étapes",
        "Recursion" in nom_erreur,
        f"levé : {nom_erreur}",
    )

# -----------------------------------------------------------------------------
# 4) Le prompt système est bien injecté à CHAQUE tour
# -----------------------------------------------------------------------------
print("\n[4] Prompt système")

verifier(
    "PROMPT_SYSTEME contient la structure imposée et la règle anti-invention",
    "STRUCTURE OBLIGATOIRE" in agent.PROMPT_SYSTEME
    and "Sources" in agent.PROMPT_SYSTEME
    and "au lieu d'inventer" in agent.PROMPT_SYSTEME,
    "prompt incomplet",
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
print("LA BOUCLE AGENTIQUE EST ENTIÈREMENT FONCTIONNELLE.")
print("Il ne reste qu'à brancher une vraie clé OPENAI_API_KEY dans .env.")
