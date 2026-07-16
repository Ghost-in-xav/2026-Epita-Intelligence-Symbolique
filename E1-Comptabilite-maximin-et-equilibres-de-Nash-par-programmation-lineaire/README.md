# Comptabilité maximin et équilibres de Nash par programmation linéaire

Projet d’intelligence symbolique consacré à l’étude algorithmique des jeux à deux joueurs, en particulier au lien entre stratégies maximin, théorème minimax, programmation linéaire et calcul d’équilibres de Nash.

Le projet est organisé sous forme de notebooks Jupyter accompagnés de fichiers de résultats issus de benchmarks expérimentaux.

## Objectifs

- Implementer l'algorithme de Lemke-Howson en Python et l'appliquer a des jeux bi-matrice 3x3 et 4x4, en visualisant les polyedres de meilleur reponse dans le simplexe
- Prouver le theoreme minimax par la dualite de la programmation lineaire (PuLP/scipy) et comparer avec la formulation directe de Nash
- Etudier la complexite du probleme de l'equilibre de Nash (classe PPAD, reduction a l'equilibre exact vs epsilon-approxime)
- Comparer les performances de Lemke-Howson, du support enumeration (Nashpy) et de l'homotopie sur un benchmark de jeux aleatoires et de jeux classiques (Battle of the Sexes, Chicken, Prisoner's Dilemma)
- Appliquer le calcul d'equilibres a un cas concret : modelisation d'un duel commercial, d'une enchere ou d'un jeu de security (allocation de ressources defensives)

## Contenu du dépôt

| Fichier | Description |
| --- | --- |
| `partie1_et_5.ipynb` | Implémentations autour des jeux matriciels, des polytopes et de l’algorithme de Lemke-Howson. |
| `partie_2.ipynb` | Étude du théorème minimax et résolution de jeux à somme nulle par programmation linéaire avec `scipy.optimize.linprog`. |
| `partie_3.ipynb` | Présentation théorique de la complexité du calcul d’un équilibre de Nash, avec introduction à PPAD. |
| `partie4.ipynb` | Benchmark de méthodes de calcul d’équilibres de Nash : Lemke-Howson, support enumeration et homotopie/logit tracing. |
| `requirements.txt` | Liste des dépendances Python nécessaires. |
| `results.csv` | Résultats bruts des benchmarks, un lancement par ligne. |
| `summary.csv` | Synthèse des benchmarks par méthode et taille de jeu. |
| `benchmark_plot.png` | Graphique comparant les temps de calcul selon les méthodes et les tailles de jeux. |

## Prérequis

- Python 3.10 ou version supérieure recommandée.
- Jupyter Notebook ou JupyterLab.
- `pip` pour installer les dépendances.

Les principales bibliothèques utilisées sont :

- `numpy`
- `scipy`
- `pandas`
- `matplotlib`
- `nashpy`

## Installation

Depuis la racine du projet :

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Si Jupyter n’est pas déjà installé dans votre environnement, vous pouvez l’ajouter avec :

```bash
pip install notebook
```

ou :

```bash
pip install jupyterlab
```

## Utilisation

Lancer Jupyter depuis la racine du dépôt :

```bash
jupyter notebook
```

ou :

```bash
jupyter lab
```

Ouvrir ensuite les notebooks dans l’ordre recommandé :

1. `partie1_et_5.ipynb`
2. `partie_2.ipynb`
3. `partie_3.ipynb`
4. `partie4.ipynb`

Chaque notebook peut être exécuté cellule par cellule. Le notebook `partie4.ipynb` génère les fichiers de benchmark :

- `results.csv`
- `summary.csv`
- `benchmark_plot.png`

## Description des principales parties

### Partie 1 et 5 — Jeux matriciels et Lemke-Howson

Cette partie introduit des outils pour manipuler des jeux à deux joueurs sous forme normale. Elle contient notamment :

- la normalisation des matrices de gains ;
- la construction de dictionnaires associés aux polytopes ;
- des opérations de pivotage ;
- l’extraction de stratégies mixtes ;
- une implémentation liée à l’algorithme de Lemke-Howson.

### Partie 2 — Théorème minimax et programmation linéaire

Cette partie se concentre sur les jeux à somme nulle. Elle présente le théorème minimax de von Neumann :

\[
\max_{\sigma \in \Delta_m} \min_{\tau \in \Delta_n} \sigma^T A \tau
=
\min_{\tau \in \Delta_n} \max_{\sigma \in \Delta_m} \sigma^T A \tau
= v
\]

La résolution est formulée comme un problème de programmation linéaire et résolue avec `scipy.optimize.linprog`.

### Partie 3 — Complexité du calcul d’un équilibre de Nash

Cette partie présente le calcul d’équilibre de Nash comme un problème de recherche totale plutôt qu’un simple problème de décision. Elle introduit notamment la classe de complexité PPAD, utilisée pour caractériser la difficulté algorithmique du calcul d’un équilibre de Nash dans les jeux finis.

### Partie 4 — Benchmarks expérimentaux

Cette partie compare plusieurs méthodes de calcul d’équilibres de Nash pour des jeux à deux joueurs :

1. **Lemke-Howson**, via `nashpy` ;
2. **Support enumeration**, via `nashpy` ;
3. **Homotopy / logit tracing**, via une implémentation dédiée.

Les jeux testés comprennent des jeux classiques 2x2 comme :

- Battle of the Sexes ;
- Chicken / Hawk-Dove ;
- Prisoner’s Dilemma ;

ainsi que des jeux aléatoires de tailles variables.

## Résultats générés

### `results.csv`

Contient les résultats détaillés de chaque exécution de benchmark :

- nom du jeu ;
- taille du jeu ;
- méthode utilisée ;
- temps d’exécution ;
- succès ou échec ;
- nombre d’équilibres retournés ;
- nombre d’équilibres valides ;
- message d’erreur éventuel.

### `summary.csv`

Agrège les résultats par méthode et par taille de jeu avec :

- temps moyen ;
- écart-type ;
- taux de succès ;
- nombre d’exécutions.

### `benchmark_plot.png`

Visualisation des temps de calcul moyens en fonction de la taille du jeu et de la méthode utilisée.

## Reproduire les benchmarks

Pour régénérer les résultats expérimentaux :

1. installer les dépendances ;
2. ouvrir `partie4.ipynb` ;
3. exécuter toutes les cellules du notebook.

Les fichiers `results.csv`, `summary.csv` et `benchmark_plot.png` seront créés ou mis à jour.

## Structure attendue de l’environnement

```text
.
├── benchmark_plot.png
├── partie1_et_5.ipynb
├── partie_2.ipynb
├── partie_3.ipynb
├── partie4.ipynb
├── requirements.txt
├── results.csv
└── summary.csv
```

## Notes

- Les notebooks utilisent des stratégies mixtes représentées par des vecteurs de probabilités.
- Certaines méthodes peuvent retourner plusieurs équilibres selon la structure du jeu.
- Les benchmarks dépendent de la machine utilisée et peuvent donc varier légèrement d’une exécution à l’autre.
