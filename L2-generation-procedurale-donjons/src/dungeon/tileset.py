"""Tileset a sockets pour le Wave Function Collapse (modele "simple tiled").

Chaque tuile expose 4 sockets (N, E, S, W) valant soit 'F' (floor, ouvert)
soit 'W' (wall, ferme). Deux tuiles adjacentes sont compatibles si leurs
sockets en vis-a-vis sont identiques. Ce modele de sockets (plutot que le
modele "overlapping" pixel-a-pixel) est celui utilise par Karth & Smith (2017)
pour la generation de donjons/circuits.
"""
from __future__ import annotations

from dataclasses import dataclass

DIRS = {"N": (0, -1), "E": (1, 0), "S": (0, 1), "W": (-1, 0)}
OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}


@dataclass(frozen=True)
class TileDef:
    name: str
    sockets: dict  # {"N": "F"|"W", "E": ..., "S": ..., "W": ...}
    is_floor: bool
    weight: float = 1.0


TILES: list[TileDef] = [
    TileDef("WALL", {"N": "W", "E": "W", "S": "W", "W": "W"}, is_floor=False, weight=5.0),
    TileDef("FLOOR", {"N": "F", "E": "F", "S": "F", "W": "F"}, is_floor=True, weight=1.0),
    TileDef("CORRIDOR_H", {"N": "W", "S": "W", "E": "F", "W": "F"}, is_floor=True, weight=2.0),
    TileDef("CORRIDOR_V", {"E": "W", "W": "W", "N": "F", "S": "F"}, is_floor=True, weight=2.0),
    TileDef("CORNER_NE", {"N": "F", "E": "F", "S": "W", "W": "W"}, is_floor=True, weight=1.2),
    TileDef("CORNER_NW", {"N": "F", "W": "F", "S": "W", "E": "W"}, is_floor=True, weight=1.2),
    TileDef("CORNER_SE", {"S": "F", "E": "F", "N": "W", "W": "W"}, is_floor=True, weight=1.2),
    TileDef("CORNER_SW", {"S": "F", "W": "F", "N": "W", "E": "W"}, is_floor=True, weight=1.2),
    TileDef("T_MISSING_S", {"N": "F", "E": "F", "W": "F", "S": "W"}, is_floor=True, weight=0.8),
    TileDef("T_MISSING_N", {"S": "F", "E": "F", "W": "F", "N": "W"}, is_floor=True, weight=0.8),
    TileDef("T_MISSING_E", {"N": "F", "S": "F", "W": "F", "E": "W"}, is_floor=True, weight=0.8),
    TileDef("T_MISSING_W", {"N": "F", "S": "F", "E": "F", "W": "W"}, is_floor=True, weight=0.8),
    TileDef("DEAD_END_N", {"N": "F", "E": "W", "S": "W", "W": "W"}, is_floor=True, weight=0.5),
    TileDef("DEAD_END_S", {"S": "F", "E": "W", "N": "W", "W": "W"}, is_floor=True, weight=0.5),
    TileDef("DEAD_END_E", {"E": "F", "N": "W", "S": "W", "W": "W"}, is_floor=True, weight=0.5),
    TileDef("DEAD_END_W", {"W": "F", "N": "W", "S": "W", "E": "W"}, is_floor=True, weight=0.5),
]


def build_compatibility() -> dict:
    """Precalcule, pour chaque direction, l'ensemble des paires de tuiles compatibles."""
    compat = {d: [set() for _ in TILES] for d in DIRS}
    for d, (dx, dy) in DIRS.items():
        opp = OPPOSITE[d]
        for i, a in enumerate(TILES):
            for j, b in enumerate(TILES):
                if a.sockets[d] == b.sockets[opp]:
                    compat[d][i].add(j)
    return compat
