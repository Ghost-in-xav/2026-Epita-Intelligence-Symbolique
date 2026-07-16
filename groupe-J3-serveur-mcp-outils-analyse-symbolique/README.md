# J3 — Serveur MCP d'outils d'analyse symbolique

> Un serveur **Model Context Protocol (MCP)** qui expose des outils d'analyse
> symbolique exacts — **SAT** (PySAT), **SMT** (Z3) et **OWL** (owlready2 +
> reasoner HermiT) — comme plugins orchestrables par un LLM via JSON-RPC.
>
> Idee directrice : le LLM ne raisonne pas « de tete », il **traduit** le
> probleme en langage naturel vers une forme symbolique, **delegue** la
> deduction a un solveur exact, puis **reformule** le resultat. On mesure la
> precision de cette chaine LLM → outil symbolique sur un benchmark de raisonnement.

EPITA SCIA — cours d'Intelligence Symbolique. Sujet **J3** (difficulte 3/5).

---

## Sommaire
- [Architecture](#architecture)
- [Installation](#installation)
- [Demarrage rapide](#demarrage-rapide)
- [Les trois outils symboliques (reference API)](#les-trois-outils-symboliques-reference-api)
- [Gestion de session](#gestion-de-session)
- [Brancher un LLM](#brancher-un-llm)
- [Evaluation](#evaluation)
- [Structure du projet](#structure-du-projet)
- [Tests](#tests)
- [Limites & perspectives](#limites--perspectives)

---

## Architecture

```
   Langage naturel                                       Langage naturel
        │ probleme                                          ▲ reponse
        ▼                                                   │
┌──────────────────┐   JSON-RPC (MCP, stdio)   ┌────────────────────────────┐
│   Hote LLM        │ ─── tools/list ─────────▶ │   Serveur MCP              │
│  Gemini / autre   │ ─── tools/call ─────────▶ │  « symbolic-analysis »     │
│  hote MCP / ...   │ ◀── resultat structure ── │  sessions │ SAT │ SMT │ OWL │
└──────────────────┘                            └────────────────────────────┘
```

Le serveur **ne contient aucun appel LLM** : il est agnostique et reutilisable
par n'importe quel hote MCP. Detail des couches et des choix de conception dans
[`docs/architecture.md`](docs/architecture.md).

---

## Installation

**Prerequis** : Python ≥ 3.10 (teste sur 3.12) et un **JRE (Java)** dans le
`PATH` — HermiT, le reasoner OWL, est un programme Java embarque par owlready2.

```bash
cd groupe-J3-serveur-mcp-outils-analyse-symbolique

# Option A — avec uv (recommande)
uv venv --python 3.12
uv pip install -r requirements.txt

# Option B — avec pip classique
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

> **Depannage.** Sur un environnement macOS Intel/Rosetta ou certains wheels ne
> se compilent pas, forcez les binaires precompiles :
> `uv pip install --only-binary=cryptography,z3-solver,python-sat -r requirements.txt`.
> Verifiez Java avec `java -version`.

Toutes les commandes ci-dessous utilisent l'interpreteur du venv (`.venv/bin/python`)
et `PYTHONPATH=src`.

### Configuration Gemini avec `.env`

Copiez le modele de configuration, puis renseignez votre clef Google AI Studio :

```bash
# Linux / macOS
cp .env.example .env
```

```powershell
# Windows PowerShell
Copy-Item .env.example .env
```

```dotenv
GEMINI_API_KEY=votre_clef
GEMINI_MODEL=gemini-2.5-flash
```

Variables acceptees :

- `GEMINI_API_KEY` : clef principale utilisee par l'hote ;
- `GOOGLE_API_KEY` : alias compatible si `GEMINI_API_KEY` est absente ;
- `GEMINI_MODEL` : modele par defaut, surchargeable avec `--model`.

Une variable definie dans le systeme ou la CI a toujours priorite sur `.env`.
Le fichier `.env` est ignore par Git : ne le committez jamais. Seul
`.env.example`, qui ne contient aucun secret, doit etre versionne.

---

## Demarrage rapide

```bash
# 1. Demo hors-ligne des 3 outils (aucune clef requise) — ideal pour decouvrir
.venv/bin/python examples/demo_offline.py

# 2. Lancer les tests (outils + couche MCP)
.venv/bin/python -m pytest -q

# 3. Verifier le pont MCP de l'hote (sans LLM)
PYTHONPATH=src .venv/bin/python -m symbolic_mcp.host.gemini_host --self-test

# 4. Explorer le serveur avec l'inspecteur MCP officiel
PYTHONPATH=src .venv/bin/mcp dev src/symbolic_mcp/server.py

# 5. Chaine complete avec un LLM (lit automatiquement le fichier .env)
PYTHONPATH=src .venv/bin/python -m symbolic_mcp.host.gemini_host \
    --prompt "Anne a le double de l'age de Bob ; dans 5 ans la somme de leurs ages sera 40. Quels ages ?"
```

---

## Les trois outils symboliques (reference API)

Chaque outil est publie via MCP avec un schema JSON-RPC. Tous acceptent un
`session_id` optionnel pour journaliser la chaine (voir [Gestion de session](#gestion-de-session)).

### `sat_solve` — satisfiabilite booleenne (PySAT)

| Parametre | Type | Defaut | Description |
|-----------|------|--------|-------------|
| `clauses` | `list[list[int]]` | *(requis)* | CNF au format DIMACS : `i` = variable *i* vraie, `-i` = fausse (indices ≥ 1). |
| `assumptions` | `list[int]` | `null` | Litteraux supposes vrais le temps de la resolution. |
| `var_names` | `dict[str,str]` | `null` | Noms lisibles des variables, ex. `{"1": "pluie"}`. |
| `max_models` | `int` | `1` | Nombre de modeles distincts a enumerer. |

```jsonc
// (pluie -> parapluie) ; pluie ; NON parapluie   ->  contradiction
{ "clauses": [[-1, 2], [1], [-2]], "var_names": {"1": "pluie", "2": "parapluie"} }
// -> { "status": "UNSAT", "summary": "UNSAT — les contraintes sont contradictoires..." }
```

### `smt_solve` — satisfiabilite modulo theories (Z3)

| Parametre | Type | Defaut | Description |
|-----------|------|--------|-------------|
| `smtlib2` | `str` | *(requis)* | Probleme au format **SMT-LIB 2** (declarations + assertions). |
| `get_model` | `bool` | `true` | Renvoyer un modele temoin si `sat`. |
| `timeout_ms` | `int` | `10000` | Budget temps du solveur. |

```jsonc
{ "smtlib2": "(declare-const x Int)(declare-const y Int)(assert (= (+ x y) 10))(assert (= (- x y) 4))" }
// -> { "status": "sat", "model": {"x": "7", "y": "3"}, "summary": "sat — ... x=7, y=3." }
```

### `owl_reason` — raisonnement ontologique (owlready2 + HermiT)

| Parametre | Type | Defaut | Description |
|-----------|------|--------|-------------|
| `ontology` | `str` | *(requis)* | Contenu de l'ontologie (texte). |
| `fmt` | `str` | `"rdfxml"` | `"rdfxml"` ou `"turtle"`. |
| `operation` | `str` | `"consistency"` | `"consistency"` \| `"classify"` \| `"query"`. |
| `target` | `str` | `null` | Classe/individu a inspecter (operation `"query"`). |

```jsonc
{ "ontology": "@prefix : <http://ex#> . :Dog rdfs:subClassOf :Animal . :rex a :Dog .",
  "fmt": "turtle", "operation": "classify" }
// -> { "consistent": true, "individual_types": {"rex": ["Animal", "Dog"]}, ... }
```

Reponse commune : chaque outil renvoie `ok`, un `summary` en langage naturel
(traduction symbolique → NL) et ses champs specifiques ; en cas d'erreur,
`ok=false` + `error` (exploitable par le LLM pour se corriger).

---

## Gestion de session

Le sujet demande de gerer *sessions et contexte*. Deux outils MCP l'exposent :

- `open_session()` → cree une session, renvoie un `session_id`.
- `session_history(session_id)` → journal des appels (outil, arguments, resultat).

En passant ce `session_id` aux outils symboliques, on obtient une **trace de la
chaine de raisonnement** multi-etapes — utile pour le debogage et l'evaluation.

---

## Brancher un LLM

Le serveur est agnostique. Deux voies sont documentees :

- **Hote Gemini** (fourni, `src/symbolic_mcp/host/gemini_host.py`) : boucle
  agentique qui connecte Gemini au serveur, convertit les schemas, laisse le LLM
  orchestrer et **trace chaque appel d'outil**.
- **Tout hote MCP de bureau** : le fichier [`docs/mcp_host_config.json`](docs/mcp_host_config.json)
  fournit la configuration `mcpServers` a copier dans votre hote MCP (remplacez les
  chemins absolus, puis redemarrez l'hote).

```bash
PYTHONPATH=src .venv/bin/python -m symbolic_mcp.host.gemini_host \
    --prompt "Les chats et les chiens sont disjoints. Felix est chat et chien. Est-ce coherent ?"
```

---

## Evaluation

Le harnais `eval/` mesure la **precision de la chaine LLM → outil** sur 11
problemes en langage naturel (SAT / SMT / OWL) a verite terrain connue, selon
trois niveaux :

| Metrique | Question |
|----------|----------|
| `selection_ok` | le LLM a-t-il appele le **bon outil** ? |
| `symbolic_ok` | l'outil a-t-il renvoye le **bon statut** (SAT/UNSAT/coherent...) ? |
| `answer_ok` | la **reponse finale** en langage naturel est-elle correcte ? |
| `chain_ok` | les trois a la fois (chaine de bout en bout). |

```bash
PYTHONPATH=src .venv/bin/python eval/run_eval.py            # tout le benchmark
PYTHONPATH=src .venv/bin/python eval/run_eval.py --limit 3  # sous-ensemble
```

Le detail par item est ecrit dans `eval/results.json`, avec une synthese par
categorie affichee en console.

Dans `expect_answer`, chaque element est un marqueur obligatoire ; une liste
imbriquee regroupe des formulations alternatives dont une seule doit apparaitre.

---

## Structure du projet

```
groupe-J3-serveur-mcp-outils-analyse-symbolique/
├── README.md                     ← ce fichier
├── requirements.txt / pyproject.toml
├── src/symbolic_mcp/
│   ├── server.py                 ← serveur MCP (FastMCP) : enregistre les outils
│   ├── session.py                ← gestion de session / contexte
│   ├── tools/
│   │   ├── sat_tool.py           ← SAT  (PySAT)
│   │   ├── smt_tool.py           ← SMT  (Z3)
│   │   └── owl_tool.py           ← OWL  (owlready2 + HermiT)
│   └── host/gemini_host.py       ← hote LLM Gemini <-> MCP (+ trace)
├── eval/
│   ├── benchmark.jsonl           ← 11 problemes a verite terrain
│   └── run_eval.py               ← scoring a 3 niveaux
├── examples/demo_offline.py      ← demo des 3 outils sans clef
├── tests/                        ← 33 tests (outils + MCP + config + evaluation + dependances)
├── docs/                         ← architecture + config hote MCP
└── slides/outline.md             ← plan de soutenance
```

---

## Tests

```bash
.venv/bin/python -m pytest -q
```

- `tests/test_tools.py` — tests unitaires des 3 solveurs/reasoner (fonctions pures).
- `tests/test_mcp_server.py` — integration : un client MCP **en memoire** liste et
  appelle les outils comme le ferait un vrai hote (sans sous-processus ni LLM),
  y compris le flux de session.

---

## Limites & perspectives

- **HermiT (OWL)** demarre une JVM et passe mal a l'echelle sur de grosses
  ontologies ; un reasoner OWL-RL pur Python (owlrl) serait un repli plus leger.
- **SMT non-lineaire** peut renvoyer `unknown` (indecidable en general).
- **Traduction NL → symbolique** : c'est le maillon faible mesure par l'evaluation
  (variable oubliee, contrainte inversee, mauvais outil). Le serveur renvoie des
  erreurs exploitables pour permettre au LLM de se corriger (re-prompt).
- **Perspectives** : verificateur de preuves (Lean), sessions persistantes,
  outils supplementaires (planificateur PDDL), benchmark elargi.

## References

- [Model Context Protocol](https://modelcontextprotocol.io/) — specification du protocole
- de Moura & Bjørner (2008), *Z3: An Efficient SMT Solver*, TACAS.
- Pan et al. (2023), *Logic-LM: Faithful Logical Reasoning with LLMs*, EMNLP.
- owlready2 — [documentation](https://owlready2.readthedocs.io/) ; HermiT reasoner.
- PySAT — [pysathq.github.io](https://pysathq.github.io/)
