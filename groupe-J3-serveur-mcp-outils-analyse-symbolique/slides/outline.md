# Plan de soutenance — J3 : Serveur MCP d'outils d'analyse symbolique

> ~12 slides / ~10 min + demo. Le plan couvre les 4 criteres de notation :
> presentation, theorie, technique, organisation.

---

### 1. Titre
- **Serveur MCP d'outils d'analyse symbolique**
- Sous-titre : *un LLM qui raisonne juste parce qu'il delegue a des solveurs exacts*
- Noms du groupe, EPITA SCIA — Intelligence Symbolique.

### 2. Le probleme
- Les LLM « hallucinent » sur le raisonnement logique/arithmetique.
- Idee : ne pas leur demander de raisonner, mais d'**orchestrer** des outils formels.
- Question du projet : *peut-on mesurer la precision d'une chaine LLM → outil symbolique ?*

### 3. Contexte theorique (critere : qualite theorique)
- **Neuro-symbolique** / tool-augmented generation (Logic-LM, PAL, ReAct).
- Les 3 familles d'outils :
  - **SAT** : satisfiabilite booleenne (CNF), NP-complet, solveurs CDCL.
  - **SMT** : satisfiabilite modulo theories (Int, Real...), DPLL(T), Z3.
  - **OWL/DL** : logiques de description, subsomption & coherence, reasoner HermiT (tableaux).
- **MCP** : protocole JSON-RPC standardise pour exposer des outils a un LLM.

### 4. Architecture (critere : technique)
- Schema en couches (cf. `docs/architecture.md`).
- Point cle : **le serveur ne contient aucun LLM** → agnostique, reutilisable
  (n'importe quel hote MCP *ou* notre hote Gemini).

### 5. Le serveur MCP & les 3 outils
- `sat_solve` (PySAT), `smt_solve` (Z3), `owl_reason` (owlready2 + HermiT).
- Gestion de session (`open_session`, `session_history`) = tracabilite de la chaine.
- Montrer un schema d'outil JSON-RPC (`tools/list`).

### 6. Traduction bidirectionnelle
- NL → symbolique : porte par les descriptions/schemas d'outils + le prompt systeme.
- Symbolique → NL : champ `summary` de chaque resultat.
- Exemple concret « parapluie » (SAT) : NL → CNF `[[-1,2],[1],[-2]]` → UNSAT → NL.

### 7. DEMO (critere : presentation + technique)
- **Plan A** : `python -m symbolic_mcp.host.gemini_host --prompt "..."` — Gemini orchestre, trace des appels d'outils.
- **Plan B** : MCP Inspector (`mcp dev src/symbolic_mcp/server.py`) — appeler les outils a la main dans l'UI web.
- **Filet** : `python examples/demo_offline.py` (aucune clef requise).

### 8. Evaluation (critere : technique)
- Benchmark `eval/` : 11 problemes (SAT/SMT/OWL), verite terrain connue.
- 3 niveaux de precision : **selection** d'outil, **correction symbolique**, **reponse** finale.
- Tableau de resultats `results.json` (a lancer avec la clef Gemini).

### 9. Analyse des erreurs de traduction
- Erreurs typiques LLM→symbolique : variable oubliee, contrainte inversee,
  mauvais outil choisi, SMT-LIB2 mal forme.
- Mecanisme de correction : le serveur renvoie une erreur exploitable → re-prompt.

### 10. Qualite technique
- Code : fonctions pures + tests (`pytest`, 33 tests : outils, MCP, config, evaluation, dependances).
- Robustesse : Turtle via rdflib, isolation `World` par requete, stdout protege.

### 11. Organisation (critere : organisation)
- Repartition des taches (SAT / SMT / OWL / hote+eval / doc).
- Activite Git : commits reguliers, PR sur le depot du cours.
- Structure du depot (`src/`, `tests/`, `eval/`, `examples/`, `docs/`).

### 12. Limites & perspectives
- Limites : reasoner HermiT lent a grande echelle ; SMT non-lineaire → `unknown`.
- Perspectives : ajouter un verificateur de preuves (Lean), cache de sessions
  persistant, plus d'outils (planificateur PDDL), benchmark plus large.
- Conclusion : le noyau symbolique **garantit** la correction, le LLM apporte le langage.
