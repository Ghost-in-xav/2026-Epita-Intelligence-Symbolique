"""Agregation de plusieurs executions."""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from .loop import LoopOutcome


@dataclass
class ConvergenceReport:
    n_runs: int
    convergence_rate: float
    mean_cycles: float | None
    stdev_cycles: float | None
    mean_initial_violations: float
    malformed_rate: float

    def render(self) -> str:
        cycles = (
            f"{self.mean_cycles:.2f} +/- {self.stdev_cycles:.2f}"
            if self.mean_cycles is not None
            else "n/a"
        )
        return (
            f"runs={self.n_runs} | convergence={self.convergence_rate:.0%} | "
            f"cycles={cycles} | violations initiales={self.mean_initial_violations:.2f} | "
            f"JSON malformes={self.malformed_rate:.0%}"
        )


def summarize(outcomes: list[LoopOutcome]) -> ConvergenceReport:
    """Le LLM est stochastique : une execution unique ne permet aucune conclusion."""
    if not outcomes:
        raise ValueError("Aucune execution a resumer.")

    converged = [o for o in outcomes if o.converged]
    counts = [float(o.n_cycles) for o in converged]
    initial = [float(o.cycles[0].n_violations) for o in outcomes if o.cycles and o.cycles[0].n_violations >= 0]
    total_cycles = sum(o.n_cycles for o in outcomes)
    malformed = sum(1 for o in outcomes for c in o.cycles if c.error)

    return ConvergenceReport(
        n_runs=len(outcomes),
        convergence_rate=len(converged) / len(outcomes),
        mean_cycles=statistics.mean(counts) if counts else None,
        stdev_cycles=statistics.stdev(counts) if len(counts) > 1 else 0.0,
        mean_initial_violations=statistics.mean(initial) if initial else 0.0,
        malformed_rate=malformed / total_cycles if total_cycles else 0.0,
    )
