"""Metriques d'evaluation automatique des niveaux generes.

Combine des criteres de jouabilite (connectivite, longueur de chemin,
absence de zones bloquees) et esthetiques (densite, variete des salles).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .grid import Grid, Tile


def _neighbors(x: int, y: int):
    yield x + 1, y
    yield x - 1, y
    yield x, y + 1
    yield x, y - 1


def reachable_from(grid: Grid, origin: tuple[int, int]) -> set[tuple[int, int]]:
    """BFS sur les tuiles marchables depuis `origin`. Renvoie l'ensemble des cellules atteintes."""
    if not grid.is_walkable(*origin):
        return set()
    seen = {origin}
    queue = deque([origin])
    while queue:
        x, y = queue.popleft()
        for nx, ny in _neighbors(x, y):
            if (nx, ny) not in seen and grid.is_walkable(nx, ny):
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


def shortest_path_length(grid: Grid, origin: tuple[int, int], target: tuple[int, int]) -> int | None:
    """Longueur du plus court chemin (BFS) en nombre de pas, ou None si inaccessible."""
    if not grid.is_walkable(*origin) or not grid.is_walkable(*target):
        return None
    if origin == target:
        return 0
    seen = {origin}
    queue = deque([(origin, 0)])
    while queue:
        (x, y), dist = queue.popleft()
        for nx, ny in _neighbors(x, y):
            if (nx, ny) == target:
                return dist + 1
            if (nx, ny) not in seen and grid.is_walkable(nx, ny):
                seen.add((nx, ny))
                queue.append(((nx, ny), dist + 1))
    return None


@dataclass
class LevelMetrics:
    connectivity_ratio: float  # fraction des tuiles marchables reellement atteintes depuis start
    is_fully_connected: bool  # start et end dans la meme composante, aucune zone bloquee
    path_length: int | None  # longueur du plus court chemin start -> end
    floor_density: float  # proportion de tuiles marchables sur la surface totale
    n_rooms: int
    room_size_variety: float  # coefficient de variation des surfaces de salles (0 = toutes identiques)
    n_dead_ends: int  # cellules marchables avec un seul voisin marchable (branchement)

    def to_dict(self) -> dict:
        return {
            "connectivity_ratio": self.connectivity_ratio,
            "is_fully_connected": self.is_fully_connected,
            "path_length": self.path_length,
            "floor_density": self.floor_density,
            "n_rooms": self.n_rooms,
            "room_size_variety": self.room_size_variety,
            "n_dead_ends": self.n_dead_ends,
        }


def count_dead_ends(grid: Grid) -> int:
    count = 0
    for y in range(grid.height):
        for x in range(grid.width):
            if not grid.is_walkable(x, y):
                continue
            n_walkable_neighbors = sum(1 for nx, ny in _neighbors(x, y) if grid.is_walkable(nx, ny))
            if n_walkable_neighbors == 1:
                count += 1
    return count


def room_size_variety(grid: Grid) -> float:
    if len(grid.rooms) < 2:
        return 0.0
    sizes = [r.w * r.h for r in grid.rooms]
    mean = sum(sizes) / len(sizes)
    if mean == 0:
        return 0.0
    variance = sum((s - mean) ** 2 for s in sizes) / len(sizes)
    return (variance ** 0.5) / mean


def evaluate(grid: Grid) -> LevelMetrics:
    total_floor = grid.floor_count()
    reached = reachable_from(grid, grid.start) if grid.start else set()
    connectivity_ratio = (len(reached) / total_floor) if total_floor else 0.0

    path_len = None
    fully_connected = False
    if grid.start and grid.end:
        path_len = shortest_path_length(grid, grid.start, grid.end)
        fully_connected = path_len is not None and connectivity_ratio >= 0.999

    return LevelMetrics(
        connectivity_ratio=connectivity_ratio,
        is_fully_connected=fully_connected,
        path_length=path_len,
        floor_density=total_floor / (grid.width * grid.height),
        n_rooms=len(grid.rooms),
        room_size_variety=room_size_variety(grid),
        n_dead_ends=count_dead_ends(grid),
    )
