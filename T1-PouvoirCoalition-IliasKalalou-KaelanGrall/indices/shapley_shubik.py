from __future__ import annotations

import math
import random
from itertools import combinations

from core.games import WeightedVotingGame


def shapley_shubik_exact(game: WeightedVotingGame) -> dict[int, float]:
    """
    Indice de Shapley-Shubik (1954) : fraction des ordres d'arrivee ou le joueur
    est pivot, calculee par SS_i = somme sur S sans i de |S|!(n-|S|-1)!/n! *
    (v(S+i) - v(S)), en O(2^n * n).
    """
    n = game.n_players
    factorial_n = math.factorial(n)
    power = {i: 0.0 for i in game.players}

    for i in game.players:
        others = [p for p in game.players if p != i]
        for size in range(len(others) + 1):
            weight = math.factorial(size) * math.factorial(n - size - 1) / factorial_n
            for combo in combinations(others, size):
                coalition = frozenset(combo)
                if game.value(coalition | {i}) > game.value(coalition):
                    power[i] += weight

    return power


def shapley_shubik_monte_carlo(
    game: WeightedVotingGame,
    n_samples: int = 100_000,
    seed: int | None = None,
) -> dict[int, float]:
    """Approximation par echantillonnage d'ordres d'arrivee, en O(n_samples * n)."""
    rng = random.Random(seed)
    pivot_counts = {i: 0 for i in game.players}
    order = list(game.players)

    for _ in range(n_samples):
        rng.shuffle(order)
        cumulative = 0
        for player in order:
            previous = cumulative
            cumulative += game.weights[player]
            if previous < game.quota <= cumulative:
                pivot_counts[player] += 1
                break

    return {i: pivot_counts[i] / n_samples for i in game.players}
