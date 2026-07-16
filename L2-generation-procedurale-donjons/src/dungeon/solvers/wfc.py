"""Generation de donjons par Wave Function Collapse (WFC).

Algorithme : a chaque etape, la cellule de plus faible entropie (le moins de
tuiles candidates) est effondree sur une tuile tiree au sort (pondere par le
poids des tuiles), puis la contrainte de compatibilite des sockets est
propagee aux voisins (a la AC-3). Une contradiction (domaine vide) declenche
un redemarrage complet avec une graine derivee -- approche "WFC with
restarts", plus simple qu'un retour-arriere complet et suffisante a l'echelle
d'une grille de donjon.

La connectivite globale n'est pas garantie par la propagation locale des
sockets : apres effondrement complet, seule la plus grande composante
connexe de sol est conservee (le reste est remure), ce qui assure
l'absence de zone bloquee/inaccessible dans le niveau final.
"""
from __future__ import annotations

import random
import time
from collections import deque

from ..grid import Grid, Tile
from ..tileset import DIRS, TILES, build_compatibility
from .base import GenerationResult, LevelGenerator

_COMPAT = build_compatibility()


class ContradictionError(Exception):
    pass


def _initial_domains(width: int, height: int) -> dict:
    domains = {}
    for y in range(height):
        for x in range(width):
            allowed = set(range(len(TILES)))
            for d, (dx, dy) in DIRS.items():
                nx, ny = x + dx, y + dy
                if not (0 <= nx < width and 0 <= ny < height):
                    # bord de la grille : le socket exterieur doit etre un mur
                    allowed = {i for i in allowed if TILES[i].sockets[d] == "W"}
            domains[(x, y)] = allowed
    return domains


def _propagate(domains: dict, width: int, height: int, start_cells) -> None:
    queue = deque(start_cells)
    in_queue = set(start_cells)
    while queue:
        cell = queue.popleft()
        in_queue.discard(cell)
        x, y = cell
        for d, (dx, dy) in DIRS.items():
            nx, ny = x + dx, y + dy
            if not (0 <= nx < width and 0 <= ny < height):
                continue
            neighbor = (nx, ny)
            possible_from_here = set()
            for t in domains[cell]:
                possible_from_here |= _COMPAT[d][t]
            new_domain = domains[neighbor] & possible_from_here
            if not new_domain:
                raise ContradictionError(f"domaine vide en {neighbor}")
            if new_domain != domains[neighbor]:
                domains[neighbor] = new_domain
                if neighbor not in in_queue:
                    queue.append(neighbor)
                    in_queue.add(neighbor)


def _run_wfc(width: int, height: int, rng: random.Random) -> list:
    domains = _initial_domains(width, height)
    cells = [(x, y) for y in range(height) for x in range(width)]

    while True:
        undecided = [c for c in cells if len(domains[c]) > 1]
        if not undecided:
            break
        min_entropy = min(len(domains[c]) for c in undecided)
        candidates = [c for c in undecided if len(domains[c]) == min_entropy]
        cell = rng.choice(candidates)

        options = list(domains[cell])
        weights = [TILES[i].weight for i in options]
        chosen = rng.choices(options, weights=weights, k=1)[0]
        domains[cell] = {chosen}
        _propagate(domains, width, height, [cell])

    return [next(iter(domains[c])) for c in cells]


def _largest_connected_floor(tile_ids: list, width: int, height: int) -> set:
    def is_floor(x, y):
        idx = y * width + x
        return TILES[tile_ids[idx]].is_floor

    visited = set()
    best_component: set = set()
    for y in range(height):
        for x in range(width):
            if (x, y) in visited or not is_floor(x, y):
                continue
            component = set()
            queue = deque([(x, y)])
            visited.add((x, y))
            while queue:
                cx, cy = queue.popleft()
                component.add((cx, cy))
                for dx, dy in DIRS.values():
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited and is_floor(nx, ny):
                        visited.add((nx, ny))
                        queue.append((nx, ny))
            if len(component) > len(best_component):
                best_component = component
    return best_component


def _farthest_pair(component: set) -> tuple:
    def bfs_farthest(source):
        dist = {source: 0}
        queue = deque([source])
        farthest, farthest_d = source, 0
        while queue:
            cx, cy = queue.popleft()
            d = dist[(cx, cy)]
            if d > farthest_d:
                farthest, farthest_d = (cx, cy), d
            for dx, dy in DIRS.values():
                np_ = (cx + dx, cy + dy)
                if np_ in component and np_ not in dist:
                    dist[np_] = d + 1
                    queue.append(np_)
        return farthest, dist

    any_cell = next(iter(component))
    a, _ = bfs_farthest(any_cell)
    b, dist_from_a = bfs_farthest(a)
    return a, b, dist_from_a


class WFCDungeonGenerator(LevelGenerator):
    name = "wfc"

    def generate(
        self,
        width: int,
        height: int,
        seed: int,
        min_connectivity_ratio: float = 0.55,
        max_attempts: int = 8,
        **_params,
    ) -> GenerationResult:
        t0 = time.perf_counter()
        rng = random.Random(seed)
        best_grid, best_ratio, attempts = None, -1.0, 0

        for attempt in range(max_attempts):
            attempts = attempt + 1
            attempt_rng = random.Random(rng.randint(0, 2**31))
            try:
                tile_ids = _run_wfc(width, height, attempt_rng)
            except ContradictionError:
                continue

            total_floor = sum(1 for t in tile_ids if TILES[t].is_floor)
            component = _largest_connected_floor(tile_ids, width, height)
            ratio = (len(component) / total_floor) if total_floor else 0.0

            grid = Grid(width=width, height=height, method="wfc", seed=seed)
            for idx, t in enumerate(tile_ids):
                x, y = idx % width, idx // width
                grid.set(x, y, Tile.FLOOR if (x, y) in component else Tile.WALL)

            if ratio > best_ratio:
                best_ratio, best_grid = ratio, grid
            if ratio >= min_connectivity_ratio and len(component) >= 4:
                break

        elapsed = time.perf_counter() - t0
        if best_grid is None:
            empty = Grid(width=width, height=height, method="wfc", seed=seed)
            return GenerationResult(grid=empty, method=self.name, seed=seed, elapsed_s=elapsed, n_attempts=attempts, solver_status="CONTRADICTION")

        component = {(x, y) for y in range(height) for x in range(width) if best_grid.get(x, y) == Tile.FLOOR}
        if len(component) >= 2:
            start, end, dist = _farthest_pair(component)
            best_grid.start = start
            best_grid.end = end
            best_grid.set(*start, Tile.START)
            best_grid.set(*end, Tile.END)
            _apply_progression(best_grid, dist, start, end, rng)

        return GenerationResult(
            grid=best_grid,
            method=self.name,
            seed=seed,
            elapsed_s=elapsed,
            n_attempts=attempts,
            solver_status="OK" if best_ratio >= min_connectivity_ratio else "PARTIAL",
        )


def _apply_progression(grid: Grid, dist_from_start: dict, start, end, rng: random.Random) -> None:
    """Place ennemis/tresors/cle-porte proportionnellement a la distance BFS au depart."""
    max_dist = max(dist_from_start.values()) if dist_from_start else 1
    max_dist = max_dist or 1
    reachable_cells = [c for c in dist_from_start if c not in (start, end)]

    key_cell = None
    for c in reachable_cells:
        progress = dist_from_start[c] / max_dist
        if 0.4 <= progress <= 0.7 and (key_cell is None or rng.random() < 0.3):
            key_cell = c
    if key_cell:
        grid.set(*key_cell, Tile.KEY)
        # porte juste avant l'arrivee : cellule marchable la plus proche de `end`
        door_candidates = sorted(
            (c for c in reachable_cells if c != key_cell),
            key=lambda c: -dist_from_start[c],
        )
        if door_candidates:
            grid.set(*door_candidates[0], Tile.DOOR)

    for c in reachable_cells:
        if c == key_cell:
            continue
        progress = dist_from_start[c] / max_dist
        if grid.get(*c) != Tile.FLOOR:
            continue
        if rng.random() < progress * 0.06:
            grid.set(*c, Tile.ENEMY)
        elif rng.random() < 0.01 + progress * 0.02:
            grid.set(*c, Tile.TREASURE)
