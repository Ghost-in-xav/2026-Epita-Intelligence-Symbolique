"""Modele de grille pour les donjons generes (tuiles, salles, serialisation)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

import numpy as np


class Tile(IntEnum):
    WALL = 0
    FLOOR = 1
    START = 2
    END = 3
    KEY = 4
    DOOR = 5
    ENEMY = 6
    TREASURE = 7


TILE_SYMBOLS = {
    Tile.WALL: "#",
    Tile.FLOOR: ".",
    Tile.START: "S",
    Tile.END: "E",
    Tile.KEY: "k",
    Tile.DOOR: "D",
    Tile.ENEMY: "x",
    Tile.TREASURE: "$",
}

# Tuiles sur lesquelles un agent peut marcher (utilise par les metriques de connectivite)
WALKABLE = {Tile.FLOOR, Tile.START, Tile.END, Tile.KEY, Tile.DOOR, Tile.ENEMY, Tile.TREASURE}


@dataclass
class Room:
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self) -> tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    @property
    def x2(self) -> int:
        return self.x + self.w - 1

    @property
    def y2(self) -> int:
        return self.y + self.h - 1

    def cells(self):
        for yy in range(self.y, self.y + self.h):
            for xx in range(self.x, self.x + self.w):
                yield xx, yy


@dataclass
class Grid:
    width: int
    height: int
    tiles: np.ndarray = field(default=None)
    rooms: list[Room] = field(default_factory=list)
    start: tuple[int, int] | None = None
    end: tuple[int, int] | None = None
    method: str = "unknown"
    seed: int = 0

    def __post_init__(self):
        if self.tiles is None:
            self.tiles = np.zeros((self.height, self.width), dtype=np.int8)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def set(self, x: int, y: int, tile: Tile) -> None:
        self.tiles[y, x] = int(tile)

    def get(self, x: int, y: int) -> Tile:
        return Tile(self.tiles[y, x])

    def is_walkable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and Tile(self.tiles[y, x]) in WALKABLE

    def to_ascii(self) -> str:
        lines = []
        for y in range(self.height):
            lines.append("".join(TILE_SYMBOLS[Tile(v)] for v in self.tiles[y]))
        return "\n".join(lines)

    def floor_count(self) -> int:
        return int(sum(1 for y in range(self.height) for x in range(self.width) if self.is_walkable(x, y)))

    def to_dict(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "tiles": self.tiles.tolist(),
            "start": self.start,
            "end": self.end,
            "method": self.method,
            "seed": self.seed,
            "n_rooms": len(self.rooms),
        }
