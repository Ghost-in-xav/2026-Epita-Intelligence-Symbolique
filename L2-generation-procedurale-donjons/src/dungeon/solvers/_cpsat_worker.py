"""Point d'entree standalone (`python -m dungeon.solvers._cpsat_worker '<json>'`) qui
resout le placement de salles CP-SAT dans un processus OS totalement independant.

Invoque via `subprocess.run` plutot que `multiprocessing` : certaines combinaisons
OR-Tools/Python/OS provoquent un segfault natif sur des solves CP-SAT repetes dans
le meme interprete, et `multiprocessing` (mode spawn) doit re-executer/re-importer
le point d'entree de l'appelant, ce qui entre en conflit avec le modele d'execution
de script de Streamlit. Un vrai sous-processus, lance via l'interpreteur courant
(`sys.executable`) et communiquant par JSON sur stdout, evite ces deux problemes :
un crash ne tue que ce processus, jamais l'appelant (UI, CLI ou tests).
"""
from __future__ import annotations

import json
import random
import sys


def solve_rooms(
    width: int,
    height: int,
    seed: int,
    n_rooms: int,
    min_room: int,
    max_room: int,
    symmetry: bool,
    time_limit_s: float,
) -> dict:
    from ortools.sat.python import cp_model

    rng = random.Random(seed)
    model = cp_model.CpModel()
    xs, ys, ws, hs = [], [], [], []
    x_intervals, y_intervals = [], []

    max_x = width - 2  # derniere colonne utilisable (colonnes 0 et width-1 restent des murs)
    max_y = height - 2  # derniere ligne utilisable (lignes 0 et height-1 restent des murs)

    for i in range(n_rooms):
        w = model.NewIntVar(min_room, max_room, f"w_{i}")
        h = model.NewIntVar(min_room, max_room, f"h_{i}")
        x = model.NewIntVar(1, max_x, f"x_{i}")
        y = model.NewIntVar(1, max_y, f"y_{i}")
        # +1 de marge pour reserver une colonne/ligne de mur entre salles adjacentes
        w_pad = model.NewIntVar(min_room + 1, max_room + 1, f"wp_{i}")
        h_pad = model.NewIntVar(min_room + 1, max_room + 1, f"hp_{i}")
        model.Add(w_pad == w + 1)
        model.Add(h_pad == h + 1)
        model.Add(x + w <= max_x + 1)
        model.Add(y + h <= max_y + 1)

        x_end = model.NewIntVar(1, max_x + max_room + 2, f"xe_{i}")
        y_end = model.NewIntVar(1, max_y + max_room + 2, f"ye_{i}")
        model.Add(x_end == x + w_pad)
        model.Add(y_end == y + h_pad)
        x_intervals.append(model.NewIntervalVar(x, w_pad, x_end, f"xi_{i}"))
        y_intervals.append(model.NewIntervalVar(y, h_pad, y_end, f"yi_{i}"))
        xs.append(x)
        ys.append(y)
        ws.append(w)
        hs.append(h)

    model.AddNoOverlap2D(x_intervals, y_intervals)

    if symmetry and n_rooms >= 2:
        # Les salles miroir partagent taille et position verticale, symetriques en x
        half = n_rooms // 2
        for i in range(half):
            j = n_rooms - 1 - i
            model.Add(ws[i] == ws[j])
            model.Add(hs[i] == hs[j])
            model.Add(ys[i] == ys[j])
            model.Add(xs[i] + xs[j] + ws[i] == width)

    # Objectif souple : variete des layouts pour une meme graine de contraintes,
    # en tirant des positions-cibles aleatoires que le solveur approche sans
    # jamais relacher les contraintes dures ci-dessus.
    deviation_terms = []
    for i in range(n_rooms):
        target_x = rng.randint(1, max_x)
        target_y = rng.randint(1, max_y)
        dev_x = model.NewIntVar(0, width, f"devx_{i}")
        dev_y = model.NewIntVar(0, height, f"devy_{i}")
        model.AddAbsEquality(dev_x, xs[i] - target_x)
        model.AddAbsEquality(dev_y, ys[i] - target_y)
        deviation_terms += [dev_x, dev_y]
    model.Minimize(sum(deviation_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    # random_seed est un champ protobuf int32 : une graine hors bornes provoque un
    # segfault cote C++ (pas d'exception Python) plutot qu'une erreur propre.
    solver.parameters.random_seed = seed % 2_147_483_647
    solver.parameters.num_workers = 1
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": "INFEASIBLE", "rooms": None}

    rooms = [
        [solver.Value(xs[i]), solver.Value(ys[i]), solver.Value(ws[i]), solver.Value(hs[i])]
        for i in range(n_rooms)
    ]
    status_str = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
    return {"status": status_str, "rooms": rooms}


def main() -> None:
    params = json.loads(sys.argv[1])
    print(json.dumps(solve_rooms(**params)))


if __name__ == "__main__":
    main()
