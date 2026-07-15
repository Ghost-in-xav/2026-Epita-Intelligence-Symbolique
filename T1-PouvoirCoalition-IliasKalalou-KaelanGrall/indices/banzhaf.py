from __future__ import annotations

from itertools import combinations

from core.games import WeightedVotingGame


def swing_counts(game: WeightedVotingGame) -> dict[int, int]:
    """Nombre de coalitions ou chaque joueur est critique (eta_i, Banzhaf 1965)."""
    counts = {i: 0 for i in game.players}
    for i in game.players:
        others = [p for p in game.players if p != i]
        for size in range(len(others) + 1):
            for combo in combinations(others, size):
                base = frozenset(combo)
                if game.is_winning(base | {i}) and not game.is_winning(base):
                    counts[i] += 1
    return counts


def banzhaf_absolute(game: WeightedVotingGame) -> dict[int, float]:
    """Probabilite que le vote du joueur soit decisif : eta_i / 2^(n-1)."""
    counts = swing_counts(game)
    denom = 2 ** (game.n_players - 1)
    return {i: counts[i] / denom for i in game.players}


def banzhaf_normalized(game: WeightedVotingGame) -> dict[int, float]:
    """Indice de Banzhaf normalise : eta_i / somme des eta_j (somme = 1)."""
    counts = swing_counts(game)
    total = sum(counts.values())
    return {i: counts[i] / total for i in game.players}
