"""Banc d'essai comparatif CP-SAT vs WFC : temps de generation et qualite des niveaux."""
from __future__ import annotations

import pandas as pd

from .generator import generate
from .metrics import evaluate

SIZE_PRESETS = {
    "small": (20, 15),
    "medium": (30, 22),
    "large": (45, 32),
}


def run_benchmark(methods: list[str], sizes: list[str], seeds: list[int], **params) -> pd.DataFrame:
    rows = []
    for method in methods:
        for size_name in sizes:
            width, height = SIZE_PRESETS[size_name]
            for seed in seeds:
                result = generate(method, width, height, seed, **params)
                m = evaluate(result.grid)
                rows.append(
                    {
                        "method": method,
                        "size": size_name,
                        "width": width,
                        "height": height,
                        "seed": seed,
                        "elapsed_s": result.elapsed_s,
                        "n_attempts": result.n_attempts,
                        "solver_status": result.solver_status,
                        **m.to_dict(),
                    }
                )
    return pd.DataFrame(rows)
