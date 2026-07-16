# M7 - Generation de contenu neuro-symbolique (Semantic Kernel + CP-SAT)

Emile Jouannet - EPITA SCIA 2026 - Intelligence Symbolique - projet solo

## Ce que fait le projet

Genere un plan de cours couvrant un syllabus, en combinant un LLM et un solveur.

Le LLM ecrit les intitules et la progression. CP-SAT verifie les contraintes dures :
couverture des objectifs, ordre des prerequis, non-chevauchement des creneaux, bornes de duree.
Quand une contrainte est violee, la violation est traduite en consigne de correction et
renvoyee au LLM. On boucle jusqu'a validite ou epuisement du budget.

Le solveur sert aussi a deux autres choses : verifier avant la boucle qu'un plan valide existe
(un cycle de prerequis rend le syllabus insoluble, et on le detecte via les literaux
d'hypothese de CP-SAT plutot que d'echouer 5 fois), et generer un plan de zero pour servir de
baseline.

## Structure

```
src/m7_neurosymbolic/
  schema.py      Syllabus, PlanCandidate, Violation
  validator.py   contraintes dures, faisabilite d'instance, solveur CSP pur
  feedback.py    violations -> consignes de correction
  generator.py   Semantic Kernel, et un generateur scripte pour les tests
  loop.py        la boucle
  baselines.py   LLM seul, CSP seul
  metrics.py     agregation sur plusieurs runs
tests/             20 tests, sans reseau
demo.ipynb         notebook explicatif
run_experiment.py  reproduit les mesures ci-dessous
data/syllabus.json exemple d'entree (8 objectifs)
```

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Pour les executions reelles seulement :

```bash
cp .env.example .env    # renseigner OPENAI_API_KEY
```

## Lancer

```bash
python -m pytest tests/ -q            # 20 tests, aucun appel reseau
python run_experiment.py --runs 10    # necessite une cle API
jupyter notebook demo.ipynb
```

Les tests utilisent `ScriptedGenerator`, qui rejoue des reponses fixees : deterministe et
gratuit. Le generateur Semantic Kernel expose la meme interface.

## Resultats

10 runs par configuration, gpt-4o-mini, budget 5 cycles, sur `data/syllabus.json`.
Donnees dans `results/experiment.json`.

| Approche | Plans valides | Cycles |
|---|---|---|
| LLM seul | 0 / 10 | 1 passe |
| LLM + feedback naif | 0 / 10 | budget epuise |
| LLM + feedback cible | 10 / 10 | 3.10 +/- 0.32 |
| CP-SAT seul | 10 / 10 par construction | 0 |

Le LLM seul oublie `ARGU` et `KR` sur les 10 runs. Ce sont les deux objectifs qui ne sont pas
sur la chaine `LOGIC -> SAT -> SMT -> VERIF` : le modele suit la progression principale et
laisse tomber les branches laterales. L'erreur est systematique, pas aleatoire.

Avec un feedback qui dit seulement "invalide, recommence", le modele recupere `ARGU` puis reste
bloque sur `KR` pendant tout le budget (9 runs sur 10 finissent avec exactement `KR` manquant).
Avec un feedback qui nomme les objectifs manquants, il converge a tous les coups. Le modele, le
solveur et la reinjection du plan precedent sont identiques dans les deux cas : seule la
formulation du feedback change.

Les trajectoires typiques sont `[1, 2, 0]` : le nombre de violations augmente avant de tomber a
zero. Ajouter l'objectif oublie decale les creneaux et casse le non-chevauchement, repare au
cycle suivant. Une passe de correction unique ne suffirait donc pas.

## Limites

- Un seul syllabus et un seul modele testes.
- N = 10 suffit a separer 0 % de 100 %, pas a donner un intervalle serre sur le nombre de cycles.
- La qualite des intitules est jugee a la lecture, pas mesuree.
- L'objectif 5 du sujet (memoire vectorielle anti-repetition) n'est pas traite.

## References

- Liang, T. et al. (2024). *LLM+Optimization: Towards Integrating Large Language Models and Optimization*. [arXiv:2401.17094](https://arxiv.org/abs/2401.17094)
- Yao, S. et al. (2023). *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR 2023. [arXiv:2210.03629](https://arxiv.org/abs/2210.03629)
- Microsoft (2024). *Semantic Kernel Documentation*. [learn.microsoft.com](https://learn.microsoft.com/en-us/semantic-kernel/)
- Notebooks CoursIA : `GenAI/SemanticKernel/01`, `03`, `05` ; `Search/Part2-CSP/CSP-6-Hybridization`
