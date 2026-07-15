from __future__ import annotations

import math

from core.games import WeightedVotingGame
from formal.smt_encoding import (
    count_swings_smt,
    enumerate_minimal_winning_smt,
    swings_by_size_smt,
)


def shapley_shubik_smt(game: WeightedVotingGame) -> dict[int, float]:
    """
    Indice de Shapley-Shubik par la voie SMT : les swings sont enumeres et
    stratifies par taille de coalition via les modeles Z3, puis ponderes par
    |S|!(n-|S|-1)!/n!.
    """
    n = game.n_players
    factorial_n = math.factorial(n)
    power = {}
    for i in game.players:
        counts = swings_by_size_smt(game, i)
        power[i] = sum(
            math.factorial(s) * math.factorial(n - s - 1) / factorial_n * c
            for s, c in counts.items()
        )
    return power


def banzhaf_smt(game: WeightedVotingGame) -> dict[int, float]:
    """Indice de Banzhaf normalise par la voie SMT (swings comptes par Z3)."""
    counts = {i: count_swings_smt(game, i) for i in game.players}
    total = sum(counts.values())
    return {i: counts[i] / total for i in game.players}


def deegan_packel_smt(game: WeightedVotingGame) -> dict[int, float]:
    """
    Indice de Deegan-Packel par la voie SMT : les coalitions gagnantes
    minimales sont enumerees par Z3 puis le pouvoir partage a parts egales.
    """
    power = {i: 0.0 for i in game.players}
    mwcs = enumerate_minimal_winning_smt(game)

    for coalition in mwcs:
        share = 1.0 / len(coalition)
        for player in coalition:
            power[player] += share

    return {i: power[i] / len(mwcs) for i in game.players}
