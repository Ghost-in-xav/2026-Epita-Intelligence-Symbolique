# L2 : génération procédurale de donjons par contraintes (CP-SAT vs Wave Function Collapse)

Générateur procédural de niveaux de type **donjon** (salles + couloirs) implémentant
**deux paradigmes de génération sous contraintes**, derrière une interface commune :

| Méthode (`--method`) | Paradigme | Garanties |
|-----------------------|-----------|-----------|
| `cpsat` | Programmation par contraintes (OR-Tools CP-SAT) : placement de salles rectangulaires sans chevauchement (`AddNoOverlap2D`), variété pilotée par un objectif souple (positions-cibles aléatoires), symétrie optionnelle en contrainte dure | Jouabilité garantie *par construction* (arbre couvrant minimal reliant toutes les salles) |
| `wfc` | Wave Function Collapse : effondrement à entropie minimale sur un tileset à sockets (16 tuiles), propagation de la compatibilité façon AC-3, redémarrage sur contradiction | Jouabilité garantie *a posteriori* (seule la plus grande composante connexe de sol est conservée) |

Les deux méthodes encodent les mêmes contraintes de **jouabilité** (accessibilité
départ → arrivée, absence de zone bloquée, difficulté progressive via une
séquence clé/porte et une densité d'ennemis/trésors croissante avec la
distance au départ) et des critères **esthétiques** (variété des tailles de
salles, symétrie, densité). L'évaluation combine des **métriques automatiques**
(connectivité, longueur du chemin, densité, variété) et se prête à une
évaluation qualitative par des joueurs humains via l'UI.

## Installation

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
```

## Utilisation

```bash
# Générer un donjon (CP-SAT, 8 salles) et afficher la grille en ASCII + métriques
dungeon-gen generate --method cpsat --width 30 --height 22 --seed 0 --rooms 8

# Variante symétrique
dungeon-gen generate --method cpsat --rooms 6 --symmetry --seed 1

# Générer par Wave Function Collapse
dungeon-gen generate --method wfc --width 30 --height 22 --seed 0

# Lancer le banc d'essai comparatif (10 graines, toutes les tailles)
dungeon-gen benchmark --methods cpsat,wfc --sizes all --seeds 10 --out benchmarks/results/results.csv

# Générer le rapport comparatif (tableaux + graphiques)
dungeon-gen report --in benchmarks/results/results.csv --out reports/report.md
```

## Interface graphique (Streamlit)

```bash
pip install -e ".[ui]"
streamlit run ui/app.py
```

- **Playground** : choisir la méthode, la taille, la graine et les paramètres
  (nombre de salles, symétrie pour CP-SAT), générer un donjon et visualiser la
  grille (sprites graphiques : salles, couloirs, départ/arrivée, clé/porte,
  ennemis, trésors — voir `ui/assets/`) avec les métriques associées.
- **Jouer** : parcourir *effectivement* le donjon généré, en tour par tour
  façon Dofus — le joueur agit une fois (déplacement, ou attaque au corps-à-corps
  s'il cible une case occupée par un monstre), puis chaque monstre agit à son
  tour (attaque s'il est adjacent, poursuite BFS s'il est à portée d'aggro,
  passif sinon). Ramasser la clé pour ouvrir la porte, collecter les trésors,
  atteindre la sortie sans tomber à 0 PV. C'est le support concret de
  l'évaluation qualitative par des joueurs humains évoquée dans le sujet.
- **Dashboard** : charger un CSV de benchmark et comparer CP-SAT vs WFC par
  taille de grille sur chaque métrique (temps, connectivité, longueur de
  chemin, densité, variété, nombre de tentatives).

## Architecture

```
src/dungeon/
  grid.py           # modele Tile/Room/Grid (tuiles, salles, serialisation, ASCII)
  metrics.py        # BFS connectivite/plus-court-chemin, densite, variete des salles, culs-de-sac
  rooms_graph.py     # arbre couvrant minimal (Prim) + boucles + creusage des couloirs en L
  tileset.py        # tileset a sockets (16 tuiles) pour le WFC + matrice de compatibilite
  solvers/
    base.py                # interface LevelGenerator + GenerationResult
    cpsat_generator.py      # generation par salles CP-SAT (OR-Tools)
    wfc.py                  # generation par Wave Function Collapse
  generator.py      # dispatch unifie generate()/generate_batch() par methode et graine
  playtest.py       # simulation jouable tour par tour (deplacement, combat, cle/porte, IA monstres)
  benchmark.py      # execution croisee methodes x tailles x graines -> DataFrame
  report.py         # agregation pandas + graphiques matplotlib -> markdown
  cli.py            # `dungeon-gen` : generate / benchmark / report
ui/
  app.py                    # interface Streamlit (playground + jouer + dashboard)
  assets/generate_assets.py # script Pillow qui dessine les sprites de tuiles/joueur
  assets/tiles/*.png        # sprites generes (mur, sol, depart, arrivee, cle, porte, ennemi, tresor, joueur)
```

### Modélisation CP-SAT

Chaque salle `i` est un rectangle `(x, y, w, h)` ; `AddNoOverlap2D` sur des
intervalles paddés de +1 empêche tout chevauchement **et** réserve une
colonne/ligne de mur entre salles adjacentes. La variété entre graines est
obtenue en minimisant l'écart (valeur absolue linéarisée via `AddAbsEquality`)
à des positions-cibles tirées aléatoirement par la graine — un objectif
*souple*, qui ne relâche jamais les contraintes dures de non-chevauchement,
de bornes ou de symétrie miroir (optionnelle). Les salles sont ensuite reliées
par un arbre couvrant minimal (Prim, distance de Manhattan entre centres) +
quelques arêtes supplémentaires pour la variété, ce qui **garantit
l'accessibilité de toutes les salles par construction** : aucune contrainte de
connectivité explicite n'est nécessaire dans le modèle CP-SAT lui-même. Le
départ et l'arrivée sont choisis par une heuristique de double-BFS
(approximation du diamètre du graphe de salles), et la difficulté (nombre
d'ennemis, présence de trésors, position de la clé/porte) est dérivée de la
distance BFS de chaque salle au départ.

### Modélisation WFC

Le tileset (16 tuiles : sol ouvert, corridors horizontaux/verticaux, coins,
jonctions en T, culs-de-sac, mur) encode des **sockets** N/E/S/W (`F`loor ou
`W`all) ; deux tuiles ne peuvent être voisines que si leurs sockets en
vis-à-vis coïncident. À chaque étape, la cellule de plus faible entropie est
effondrée (tirage pondéré par le poids des tuiles), puis la contrainte est
propagée aux voisins façon AC-3 ; une contradiction (domaine vide) déclenche
un redémarrage complet avec une graine dérivée plutôt qu'un retour-arrière
fin. Contrairement au CP-SAT, la propagation locale des sockets ne garantit
**pas** la connectivité globale : seule la plus grande composante connexe de
sol est conservée après effondrement (le reste est remuré), ce qui assure
l'absence de zone inaccessible dans le niveau livré. Le départ/l'arrivée sont
choisis par double-BFS sur les cellules de cette composante.

### Mode jouable (tour par tour façon Dofus)

`playtest.py` transforme la grille générée en petite simulation jouable :
chaque tuile `ENEMY` de la grille statique devient une entité mobile
indépendante (sa case redevient du sol). Un tour se déroule ainsi : le joueur
agit une fois (déplacement dans une direction, ou attaque au corps-à-corps
s'il vise une case occupée par un monstre), **puis** chaque monstre encore en
vie agit à son tour — il attaque si le joueur est adjacent, se rapproche par
plus-court-chemin (BFS) s'il est à portée d'aggro, ou reste passif sinon. La
clé doit être ramassée pour franchir la porte (contrainte de progression déjà
encodée par les générateurs), les trésors incrémentent un score, et la partie
se termine par une victoire (sortie atteinte) ou une défaite (PV à 0).

## Tests

```bash
pytest -q
```

Les tests vérifient : la non-superposition et les bornes des salles CP-SAT,
la contrainte de symétrie, la diversité entre graines, la connectivité totale
(CP-SAT et WFC) via BFS, la symétrie de la matrice de compatibilité WFC, les
métriques (BFS de connectivité/plus court chemin, comptage des culs-de-sac,
variété des tailles de salles) sur des grilles de référence, et la simulation
jouable (déplacement, combat, ramassage clé/trésor, ouverture de porte,
victoire/défaite, comportement d'IA des monstres).

## Évaluation

Le banc d'essai (`dungeon-gen benchmark`) exécute les deux méthodes sur
plusieurs tailles de grille (`small`/`medium`/`large`) et graines, puis
mesure : temps de génération, nombre de tentatives (retries WFC en cas de
contradiction), ratio de connectivité, longueur du chemin départ → arrivée,
densité de sol et variété des tailles de salles. Le rapport (`dungeon-gen
report`) agrège ces résultats en tableaux et graphiques comparatifs — voir
[`reports/report.md`](reports/report.md) après exécution du benchmark.
L'évaluation qualitative (jouabilité perçue, lisibilité, plaisir de jeu) est
laissée aux retours de joueurs humains via l'UI Streamlit.

## Références

- Karth, I. & Smith, A.M. (2017). "WaveFunctionCollapse is Constraint Solving
  in the Wild." *FDG 2017*.
- Togelius, J. et al. (2011). "Search-Based Procedural Content Generation."
  *IEEE TCIAIG*.
- Shaker, N. et al. (2016). *Procedural Content Generation in Games*.
  Springer.
- Smith, A.M. & Mateas, M. (2011). "Answer Set Programming for Procedural
  Content Generation." *IEEE T-CIAIG*.
