"""Point d'entree unifie : selection du paradigme et generation multi-graines."""
from __future__ import annotations

from .solvers import REGISTRY
from .solvers.base import GenerationResult


def generate(method: str, width: int, height: int, seed: int, **params) -> GenerationResult:
    if method not in REGISTRY:
        raise ValueError(f"methode inconnue '{method}', choisir parmi {list(REGISTRY)}")
    generator = REGISTRY[method]()
    return generator.generate(width, height, seed, **params)


def generate_batch(method: str, width: int, height: int, seeds: list[int], **params) -> list[GenerationResult]:
    """Genere plusieurs niveaux diversifies en faisant varier la graine aleatoire."""
    return [generate(method, width, height, seed, **params) for seed in seeds]
