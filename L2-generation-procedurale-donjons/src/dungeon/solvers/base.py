"""Interface commune aux generateurs de niveaux (CP-SAT, WFC, ...)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from ..grid import Grid


@dataclass
class GenerationResult:
    grid: Grid
    method: str
    seed: int
    elapsed_s: float
    n_attempts: int = 1  # nombre d'essais/retries internes avant obtention d'un niveau valide
    solver_status: str = "OK"


class LevelGenerator(ABC):
    """Un generateur produit une Grid a partir d'une taille, d'une graine et de parametres
    de contraintes de jouabilite/esthetique."""

    name: str = "base"

    @abstractmethod
    def generate(self, width: int, height: int, seed: int, **params) -> GenerationResult:
        raise NotImplementedError
