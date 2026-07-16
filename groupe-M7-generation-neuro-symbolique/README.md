# M7 - Generation de contenu neuro-symbolique par Semantic Kernel + validation CSP

Emile Jouannet - EPITA SCIA 2026 - Intelligence Symbolique (projet solo)

## Le probleme

Un LLM produit un plan de cours qui se lit bien : titres pertinents, progression plausible.
Mais il oublie des objectifs quand le syllabus grandit, et se trompe sur l'ordre des prerequis
sans jamais le signaler.

Un solveur CSP garantit ces proprietes, mais produit "Session 1, Session 2" et des
regroupements arbitraires.

Ce projet combine les deux : le LLM propose, CP-SAT verifie, et les violations repartent dans
le prompt sous forme de consignes de correction.

## Le domaine

Generer un plan de cours couvrant un syllabus, sous quatre contraintes dures :

| Contrainte | Ce que le LLM rate |
|---|---|
| Couverture : chaque objectif apparait au moins une fois | Il en oublie silencieusement |
| Prerequis : un objectif vient apres tous ses prerequis | Les chaines transitives |
| Non-chevauchement des creneaux | L'arithmetique des creneaux |
| Duree dans les bornes | Derive sur les longs syllabus |

La qualite des titres et de la progression reste au LLM : c'est ce qu'il fait bien, et ca ne se
verifie pas par un solveur. Cette repartition dur/souple est l'argument du projet.

## Architecture

```
syllabus.json
     |
     v
  Generator  (Semantic Kernel -> LLM, ou ScriptedGenerator pour les tests)
     |  plan JSON
     v
  Validator  (CP-SAT)
     |  violations
     v
  valide ? --oui--> plan final
     |
    non
     v
  build_feedback --> prompt enrichi --> (boucle)
```

### Pourquoi CP-SAT et pas trois `if`

Verifier un plan complet ne demande pas de solveur : l'affectation est totale, des
verifications directes suffisent et donnent de meilleurs messages. Le solveur sert ailleurs :

- `is_instance_feasible()` repond a "existe-t-il **un** plan valide pour ce syllabus ?". Chaque
  arc de prerequis est pose sous un literal d'hypothese ; si le modele est infaisable, CP-SAT
  rend le sous-ensemble d'hypotheses responsable via `SufficientAssumptionsForInfeasibility()`.
  Sur un cycle `A -> B -> A`, on obtient les deux arcs fautifs, pas juste "infaisable". Sans ce
  garde-fou, un syllabus cyclique ferait echouer la boucle 5 fois sans explication.
- `solve()` construit un plan de zero : c'est la baseline CSP pur.

## Structure

```
src/m7_neurosymbolic/
  schema.py      modele de domaine (Syllabus, PlanCandidate, Violation)
  validator.py   contraintes dures, faisabilite d'instance, solveur CSP pur
  feedback.py    violations -> consignes de correction (+ temoin naif)
  generator.py   Semantic Kernel, et generateur scripte pour les tests
  loop.py        la boucle
  baselines.py   LLM seul, CSP seul
  metrics.py     agregation sur plusieurs runs
tests/           20 tests, sans reseau ni cle API
demo.ipynb       notebook explicatif (executable sans cle)
data/syllabus.json
```

## Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Pour l'execution reelle uniquement :

```bash
cp .env.example .env    # renseigner OPENAI_API_KEY
```

## Tests

```bash
python -m pytest tests/ -q
```

Les tests utilisent `ScriptedGenerator`, qui rejoue des reponses fixees. Aucun appel reseau,
resultats deterministes, cout nul. Le vrai generateur expose la meme interface.

## Etat

Fait :

- validateur complet (5 familles de violations) et teste
- detection d'infaisabilite d'instance par noyau CP-SAT
- boucle complete, verifiee de bout en bout avec generateur scripte
- baselines LLM-seul et CSP-seul
- notebook explicatif, execute

A faire :

- executions LLM reelles et mesures de convergence (objectif 3)
- ablation feedback cible / feedback naif
- evaluation de la qualite semantique des plans finaux : elle ne se mesure pas
  automatiquement. Une grille manuelle sur une dizaine de plans est le choix retenu, avec sa
  subjectivite assumee.
- objectif 5 (memoire vectorielle anti-repetition) : non traite

## References

- Liang, T. et al. (2024). *LLM+Optimization: Towards Integrating Large Language Models and Optimization*. [arXiv:2401.17094](https://arxiv.org/abs/2401.17094)
- Yao, S. et al. (2023). *ReAct: Synergizing Reasoning and Acting in Language Models*. ICLR 2023. [arXiv:2210.03629](https://arxiv.org/abs/2210.03629)
- Microsoft (2024). *Semantic Kernel Documentation*. [learn.microsoft.com](https://learn.microsoft.com/en-us/semantic-kernel/)
- Notebooks CoursIA : `GenAI/SemanticKernel/01`, `03`, `05` ; `Search/Part2-CSP/CSP-6-Hybridization`
