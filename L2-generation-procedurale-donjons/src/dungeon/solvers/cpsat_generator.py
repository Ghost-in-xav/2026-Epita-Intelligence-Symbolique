"""Generation de donjons par programmation par contraintes (OR-Tools CP-SAT).

Modelisation : chaque salle est un rectangle place sans chevauchement
(AddNoOverlap2D). La variete des donjons pour une meme graine de contraintes
est obtenue en minimisant l'ecart a des positions-cibles tirees aleatoirement
(objectif souple), tandis que les contraintes de non-chevauchement, de bornes
et (optionnellement) de symetrie restent des contraintes dures satisfaites
exactement par le solveur.

La jouabilite (accessibilite start->end, absence de zone bloquee) est garantie
par construction : les salles sont reliees par un arbre couvrant minimal
(voir `rooms_graph.py`), qui connecte toutes les salles entre elles.
La difficulte progressive est encodee en repartissant ennemis/tresors selon
la distance (BFS dans le graphe de salles) a la salle de depart.

Le solve CP-SAT proprement dit est isole dans un processus independant
(`subprocess.run`, voir `_cpsat_worker.py`). Certaines combinaisons
OR-Tools/Python/OS provoquent un segfault natif (crash C++, sans exception
Python) en cas de solves CP-SAT repetes dans le meme interpreteur --
typiquement reproductible dans une UI Streamlit qui reste en vie entre les
interactions. Un vrai sous-processus OS (plutot que `multiprocessing`, dont le
mode "spawn" doit re-executer/re-importer le point d'entree de l'appelant --
ce qui entre en conflit avec le modele d'execution de script de Streamlit)
contient le crash sans jamais tuer l'appelant, et donne a chaque generation un
interprete natif frais.
"""
from __future__ import annotations

import json
import random
import subprocess
import sys
import time

from ..grid import Grid, Room, Tile
from ..rooms_graph import (
    add_extra_loops,
    carve_corridor,
    carve_room,
    graph_distances_from,
    minimum_spanning_tree,
    pick_start_end,
)
from .base import GenerationResult, LevelGenerator


def _solve_rooms(
    width: int,
    height: int,
    seed: int,
    n_rooms: int,
    min_room: int,
    max_room: int,
    symmetry: bool,
    time_limit_s: float,
):
    """Delegue le solve CP-SAT a `_cpsat_worker.py` dans un processus OS independant.

    Renvoie (status_str, rooms) ou `rooms` est une liste de tuples (x, y, w, h),
    ou None si aucune solution (infaisable, timeout ou crash natif du sous-processus)."""
    params = {
        "width": width,
        "height": height,
        "seed": seed,
        "n_rooms": n_rooms,
        "min_room": min_room,
        "max_room": max_room,
        "symmetry": symmetry,
        "time_limit_s": time_limit_s,
    }
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "dungeon.solvers._cpsat_worker", json.dumps(params)],
            capture_output=True,
            text=True,
            timeout=time_limit_s + 15.0,
        )
    except subprocess.TimeoutExpired:
        return "TIMEOUT", None

    if proc.returncode != 0 or not proc.stdout.strip():
        return "CRASHED", None
    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return "CRASHED", None

    rooms = payload.get("rooms")
    if rooms is None:
        return payload.get("status", "INFEASIBLE"), None
    return payload["status"], [tuple(r) for r in rooms]


class CPSATDungeonGenerator(LevelGenerator):
    name = "cpsat"

    def generate(
        self,
        width: int,
        height: int,
        seed: int,
        n_rooms: int = 8,
        min_room: int = 3,
        max_room: int = 7,
        symmetry: bool = False,
        time_limit_s: float = 5.0,
        **_params,
    ) -> GenerationResult:
        t0 = time.perf_counter()
        rng = random.Random(seed)

        status_str, room_tuples = _solve_rooms(
            width, height, seed, n_rooms, min_room, max_room, symmetry, time_limit_s
        )

        grid = Grid(width=width, height=height, method="cpsat", seed=seed)
        if room_tuples is None:
            elapsed = time.perf_counter() - t0
            return GenerationResult(grid=grid, method=self.name, seed=seed, elapsed_s=elapsed, solver_status=status_str)

        rooms = [Room(x=x, y=y, w=w, h=h) for x, y, w, h in room_tuples]
        grid.rooms = rooms
        for room in rooms:
            carve_room(grid, room)

        mst_edges = minimum_spanning_tree(rooms)
        edges = add_extra_loops(rooms, mst_edges, rng)
        for a, b in edges:
            carve_corridor(grid, rooms[a], rooms[b], rng)

        start_idx, end_idx = pick_start_end(len(rooms), mst_edges)
        distances = graph_distances_from(len(rooms), mst_edges, start_idx)
        max_dist = max(d for d in distances if d >= 0) or 1

        start_room, end_room = rooms[start_idx], rooms[end_idx]
        grid.start = start_room.center
        grid.end = end_room.center
        grid.set(*grid.start, Tile.START)
        if end_idx != start_idx:
            # Avec un seul donjon a une salle, start_idx == end_idx : ne pas ecraser START.
            grid.set(*grid.end, Tile.END)

        key_room_idx = None
        for i, d in enumerate(distances):
            if i in (start_idx, end_idx):
                continue
            if 0 < d < max_dist and (key_room_idx is None or d > distances[key_room_idx]):
                key_room_idx = i
        if key_room_idx is not None:
            kx, ky = rooms[key_room_idx].center
            if (kx, ky) not in (grid.start, grid.end):
                grid.set(kx, ky, Tile.KEY)
            grid.set(*_room_edge_cell(rooms[end_idx], rng), Tile.DOOR)

        for i, room in enumerate(rooms):
            if i in (start_idx, end_idx, key_room_idx):
                continue
            progress = distances[i] / max_dist if max_dist else 0.0
            n_enemies = round(progress * 3)
            cells = [c for c in room.cells() if grid.get(*c) == Tile.FLOOR]
            rng.shuffle(cells)
            for cx, cy in cells[:n_enemies]:
                grid.set(cx, cy, Tile.ENEMY)
            if rng.random() < progress and len(cells) > n_enemies:
                tx, ty = cells[n_enemies]
                grid.set(tx, ty, Tile.TREASURE)

        elapsed = time.perf_counter() - t0
        return GenerationResult(
            grid=grid,
            method=self.name,
            seed=seed,
            elapsed_s=elapsed,
            solver_status=status_str,
        )


def _room_edge_cell(room: Room, rng: random.Random) -> tuple[int, int]:
    # Exclut explicitement le centre (deja occupe par START/END) : sur une petite salle
    # (w ou h == 2), le centre entier fait aussi partie du perimetre (c[0]==room.x2
    # quand room.center[0] == room.x2), ce qui l'inclurait sinon dans edge_cells.
    center = room.center
    edge_cells = [
        c for c in room.cells() if c != center and (c[0] in (room.x, room.x2) or c[1] in (room.y, room.y2))
    ]
    return rng.choice(edge_cells) if edge_cells else center
