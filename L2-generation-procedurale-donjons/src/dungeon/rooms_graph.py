"""Connexion des salles (graphe + arbre couvrant minimal) et creusage des couloirs.

Partage entre generateurs a base de salles (CP-SAT). Garantit par construction
qu'aucune salle n'est isolee : l'arbre couvrant minimal relie toutes les salles,
et des aretes supplementaires (boucles) sont ajoutees pour la variete.
"""
from __future__ import annotations

import random

from .grid import Grid, Room, Tile


def _dist(a: Room, b: Room) -> float:
    ax, ay = a.center
    bx, by = b.center
    return abs(ax - bx) + abs(ay - by)


def minimum_spanning_tree(rooms: list[Room]) -> list[tuple[int, int]]:
    """Prim's algorithm sur les centres des salles. Renvoie une liste d'aretes (i, j)."""
    n = len(rooms)
    if n <= 1:
        return []
    in_tree = {0}
    edges: list[tuple[int, int]] = []
    while len(in_tree) < n:
        best = None
        best_d = float("inf")
        for i in in_tree:
            for j in range(n):
                if j in in_tree:
                    continue
                d = _dist(rooms[i], rooms[j])
                if d < best_d:
                    best_d = d
                    best = (i, j)
        edges.append(best)
        in_tree.add(best[1])
    return edges


def add_extra_loops(rooms: list[Room], mst_edges: list[tuple[int, int]], rng: random.Random, extra_ratio: float = 0.2) -> list[tuple[int, int]]:
    """Ajoute des aretes non-MST (boucles) pour la variete, sans casser la connectivite."""
    n = len(rooms)
    existing = {frozenset(e) for e in mst_edges}
    candidates = [(i, j) for i in range(n) for j in range(i + 1, n) if frozenset((i, j)) not in existing]
    rng.shuffle(candidates)
    n_extra = int(len(mst_edges) * extra_ratio)
    return mst_edges + candidates[:n_extra]


def graph_distances_from(n: int, edges: list[tuple[int, int]], source: int) -> list[int]:
    """BFS non pondere sur le graphe de salles."""
    adjacency: dict[int, list[int]] = {i: [] for i in range(n)}
    for a, b in edges:
        adjacency[a].append(b)
        adjacency[b].append(a)
    dist = [-1] * n
    dist[source] = 0
    queue = [source]
    head = 0
    while head < len(queue):
        u = queue[head]
        head += 1
        for v in adjacency[u]:
            if dist[v] == -1:
                dist[v] = dist[u] + 1
                queue.append(v)
    return dist


def pick_start_end(n: int, edges: list[tuple[int, int]]) -> tuple[int, int]:
    """Heuristique du double-BFS pour approximer le diametre du graphe de salles."""
    d0 = graph_distances_from(n, edges, 0)
    a = max(range(n), key=lambda i: d0[i])
    da = graph_distances_from(n, edges, a)
    b = max(range(n), key=lambda i: da[i])
    return a, b


def carve_room(grid: Grid, room: Room, tile: Tile = Tile.FLOOR) -> None:
    for x, y in room.cells():
        grid.set(x, y, tile)


def carve_corridor(grid: Grid, a: Room, b: Room, rng: random.Random) -> None:
    """Couloir en L (largeur 1) entre les centres de deux salles, coude horizontal ou vertical au hasard."""
    ax, ay = a.center
    bx, by = b.center
    horizontal_first = rng.random() < 0.5

    def carve_h(y: int, x1: int, x2: int) -> None:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            if grid.get(x, y) == Tile.WALL:
                grid.set(x, y, Tile.FLOOR)

    def carve_v(x: int, y1: int, y2: int) -> None:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            if grid.get(x, y) == Tile.WALL:
                grid.set(x, y, Tile.FLOOR)

    if horizontal_first:
        carve_h(ay, ax, bx)
        carve_v(bx, ay, by)
    else:
        carve_v(ax, ay, by)
        carve_h(by, ax, bx)
