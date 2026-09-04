# 🤖 TP Semaine 20 — Agent Analyste Financier

**Formation Ingénieur Data & IA — Mois 5 · Semaine 20 · Agents AI & Orchestration**

Un agent **autonome** construit avec **LangGraph** qui, à partir du nom d'une
entreprise : **planifie** ses étapes, **appelle des outils** (SQL, web,
calculs, graphique), **mémorise** sa progression et **rédige un rapport
financier structuré et sourcé**.

---

## 🚀 Démarrage rapide (5 commandes)

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Créer la base financière SQLite
python data/creer_base.py

# 3. (recommandé) Tester chaque outil séparément — conseil du cours
python test_outils.py

# 4. Tester la boucle agentique complète, SANS clé API (LLM fictif)
python test_agent_mock.py

# 5. Configurer ta clé OpenAI puis lancer une vraie analyse
cp .env.example .env      # puis édite .env : OPENAI_API_KEY=sk-...
python run.py "TechNova Solutions" --pdf
```

> 💡 Sur le shell Windows, remplace `cp` par `copy`.

---

## 📂 Structure du projet (celle du support de cours)

```
agent_analyste/
├── outils.py            # Étapes 1-2 : les outils (@tool) — web, SQL, calcul, graphe
├── agent.py             # Étapes 3-4, 6-7 : graphe LangGraph + mémoire + garde-fous
├── run.py               # Étape 5 : point d'entrée (stream en direct, sauvegarde)
├── export_pdf.py        # Bonus Niveau 3 : rapport markdown -> PDF daté
├── data/
│   ├── creer_base.py    # Script de création de la base SQLite (5 entreprises)
│   └── finances.db      # La base (générée par le script)
├── rapport/             # Rapports générés (markdown, PDF, graphe_ca.png)
├── logs/
│   └── agent.log        # Journalisation de toutes les requêtes (garde-fou)
├── test_outils.py       # TEST 1 : chaque outil isolé (18 vérifications)
├── test_agent_mock.py   # TEST 2 : boucle agentique complète sans clé API (11)
├── test_prompt_reel.py  # TEST 3 : prompt système validé par un vrai LLM (6)
├── test_export_pdf.py   # TEST 4 : export PDF (3)
├── .env.example         # Modèle de configuration de la clé API
└── requirements.txt     # Dépendances
```

## 🧪 Les 4 tests (38 vérifications au total)

| Test | Ce qu'il prouve | Clé API ? |
|------|-----------------|-----------|
| `test_outils.py` | SQL lecture seule (DROP/INSERT refusés), calculs exacts, web, graphe | Non |
| `test_agent_mock.py` | Boucle ReAct complète, mémoire (MemorySaver), garde-fou anti-boucle | Non |
| `test_prompt_reel.py` | Le prompt système guide un VRAI LLM vers la bonne méthode | CLI z-ai |
| `test_export_pdf.py` | Le bonus PDF produit un fichier PDF valide | Non |

## 🧠 Rappel du concept (Jour 1 du cours)

```
        ┌─────────────────────────── boucle ReAct ───────────────────────┐
        │                                                                │
        ▼                                                                │
   ┌─────────┐    tool_call      ┌─────────┐   ToolMessage   ┌──────────┐│
   │  agent  │ ───────────────►  │ outils  │ ──────────────► │  agent   ││
   │ (LLM)   │                   │(code réel)│  observation  │ relit et │┘
   └────┬────┘                   └─────────┘                 │ décide  │
        │  pas de tool_call => le rapport est prêt           └─────────┘
        ▼
       END  ──► rapport markdown (+ PDF en bonus)
```

- **Mémoire de travail** : `MemorySaver` + `thread_id` (l'historique complet
  des messages est rejoué à chaque tour).
- **Garde-fous** : `recursion_limit=25` étapes max, SQL en lecture seule
  (double barrière : Python + SQLite `mode=ro`), erreurs explicites
  (l'agent se corrige au lieu de planter), journalisation dans `logs/`.

## 🏗️ Grille d'évaluation couverte

| Critère | Où dans le code | Points |
|---------|-----------------|--------|
| Outils fonctionnels | `outils.py` + `test_outils.py` | 20 % |
| Boucle agentique | `agent.py` + `test_agent_mock.py` | 20 % |
| Mémoire & planification | `MemorySaver`, `thread_id`, prompt MÉTHODE | 15 % |
| Rapport sourcé | `PROMPT_SYSTEME` (structure + sources obligatoires) | 25 % |
| Garde-fous | lecture seule, `recursion_limit`, erreurs explicites | 10 % |
| Bonus | graphe CA (N1) + export PDF (N3) | 10 % |

## ⚠️ Pièges classiques (déjà gérés ici)

1. **Boucle infinie** → `recursion_limit` dans la config d'invocation.
2. **SQL destructif** → refus de tout sauf `SELECT/WITH` + SQLite `mode=ro`.
3. **Résultats d'outils trop longs** → `LIMIT 50` auto + extraits tronqués.
4. **Erreur réseau de la recherche web** → message explicite, l'agent continue.
5. **Chiffres inventés** → le prompt impose la source de chaque chiffre.
