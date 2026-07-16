# M1 — Pipeline LLM + vérificateur symbolique pour la génération fiable

Un pipeline en deux étapes pour la **génération fiable** : un LLM propose une
solution candidate (en langage naturel / JSON), puis un **vérificateur symbolique
(Z3)** valide *formellement* sa correction. En cas de rejet, le pipeline
**re-prompte** le LLM selon différentes stratégies — dont une boucle
neuro-symbolique guidée par contre-exemple (CEGIS), où les contraintes violées
détectées par Z3 sont renvoyées au LLM comme signal correctif.

Sujet M1 de la catégorie *IA Neuro-Symbolique* (« LLM-as-a-reasoner »).

## Idée centrale

```
        statement (NL)              candidate (JSON)             verdict
  ┌────────────────────┐  prompt   ┌──────────────┐  parse   ┌──────────────────┐
  │      Problem       │ ────────► │     LLM      │ ───────► │  Z3 verifier     │
  │ (NL + Z3 ground    │           │ (generator)  │          │ accept / reject  │
  │  truth, hidden)    │ ◄──────── │              │ ◄─────── │ + counterexample │
  └────────────────────┘  re-prompt└──────────────┘ feedback └──────────────────┘
```

Le LLM ne voit **jamais** le modèle Z3 : il doit *raisonner* jusqu'à une
affectation, que le vérificateur accepte ou rejette de façon rigoureuse (chaque
contrainte est instanciée puis simplifiée en `True`/`False`).

## Changer de fournisseur LLM à la volée

Tous les backends parlent l'**API OpenAI-compatible** (Chat Completions). On garde
**un seul client** et on change juste `base_url` + `model` + clé. Sélection via
`--provider` :

| `--provider`           | endpoint                          | clé             |
|------------------------|-----------------------------------|-----------------|
| `anthropic` (défaut)   | `api.anthropic.com/v1` (compat.)  | `ANTHROPIC_API_KEY` |
| `openai`               | API OpenAI                        | `OPENAI_API_KEY`    |
| `ollama`               | `localhost:11434/v1` (local)      | —               |
| `openrouter`           | OpenRouter                        | `OPENROUTER_API_KEY`|
| `local`                | `localhost:8000/v1` (vLLM…)       | —               |
| `mock`                 | oracle Z3 hors-ligne (sans clé)   | —               |
| `https://…/v1`         | n'importe quel endpoint compatible| `--api-key-env` |

```bash
m1 solve linear_arith --provider anthropic --model claude-sonnet-4-6
m1 solve linear_arith --provider openai    --model gpt-4o-mini
m1 solve linear_arith --provider ollama    --model llama3.1
m1 solve linear_arith --provider https://my-host/v1 --api-key-env MY_KEY --model x
```

## Installation

```bash
cd projects/M1-llm-symbolic-verifier
uv sync                 # ajoute --extra dev pour pytest, --extra cpsat pour OR-Tools
cp .env.example .env    # renseigner la/les clé(s) du fournisseur voulu
```

## Utilisation

```bash
uv run m1 list                       # les problèmes du benchmark
uv run m1 providers                  # presets de fournisseurs + stratégies

# Démo SANS clé API (oracle Z3 déterministe), avec 2 échecs simulés avant succès :
uv run m1 solve magic_square --provider mock --mock-fail-first 2

# Avec un vrai LLM :
uv run m1 solve knights_knaves --provider anthropic --strategy counterexample

# Benchmark complet (toutes stratégies) + rapports :
uv run m1 bench --provider anthropic --max-attempts 3 \
    --json-out report.json --md-out report.md
```

## Démo live (UI web)

Une interface web qui **streame chaque tentative en direct** (Server-Sent Events) :
on voit la tentative 1 rejetée avec les contraintes Z3 violées, puis le re-prompt
qui corrige. Idéale pour une présentation.

```bash
uv run m1 serve                 # puis ouvrir http://127.0.0.1:8000
```

Astuce démo **sans clé API** : choisir le fournisseur `mock` avec « échecs forcés »
= 2 pour montrer la boucle CEGIS (2 rejets → correction) de façon déterministe.

## Stratégies de re-prompting

| stratégie          | idée |
|--------------------|------|
| `direct`           | une seule requête → JSON (contrôle) |
| `few_shot`         | direct + exemple résolu (baseline LLM seul) |
| `chain_of_thought` | raisonnement étape par étape puis réponse |
| `reformulation`    | au retry, reformule les contraintes en checklist explicite |
| `decomposition`    | résolution variable par variable, incrémentale |
| `counterexample`   | renvoie au LLM les contraintes violées par Z3 (boucle CEGIS) |

## Métriques (sous-jacentes au sujet)

- **taux de rejet** : part des générations rejetées par le vérificateur ;
- **taux de correction finale** (solve rate) : problèmes résolus en ≤ N essais ;
- **nombre moyen d'essais** jusqu'à la solution ;
- **analyse d'erreurs** : `parse_error` / `schema_error` / `constraint_violation` ;
- **baselines** : LLM seul (zero-shot / few-shot = 1 essai) et **solveur seul**
  (Z3, l'oracle, ~100 % sur les problèmes satisfiables).

## Benchmark

7 problèmes couvrant plusieurs paradigmes, avec un piège **insatisfiable**
(pigeonnier) qui vérifie que le pipeline n'accepte jamais une réponse
hallucinée :

`knights_knaves` (logique booléenne), `zebra_mini` (grille logique),
`graph_coloring` (CSP), `scheduling` (ordonnancement), `linear_arith`
(arithmétique SMT), `magic_square` (CSP arithmétique), `unsat_trap` (UNSAT).

## Architecture

```
src/m1_pipeline/
  llm/            client OpenAI-compatible unique + presets + oracle hors-ligne
  problems/       spécifications (NL + ground truth Z3) et bibliothèque
  parsing.py      extraction du JSON depuis la sortie LLM
  verifier.py     vérification symbolique Z3 + solve() (oracle)
  strategies.py   stratégies de re-prompting
  pipeline.py     boucle générer → vérifier → re-prompter
  evaluate.py     harness de benchmark, métriques, baselines
  web.py          UI web de démo live (FastAPI + SSE)
  cli.py          interface `m1`
tests/            pytest (hors-ligne, sans clé API)
```

## Références

- Pan et al. (2023), *Logic-LM: Faithful Logical Reasoning with LLMs*, EMNLP.
- Garcez et al. (2024), *Neurosymbolic AI: The 3rd Wave*, AI Review.
- de Moura & Bjørner (2008), *Z3: An Efficient SMT Solver*, TACAS.
