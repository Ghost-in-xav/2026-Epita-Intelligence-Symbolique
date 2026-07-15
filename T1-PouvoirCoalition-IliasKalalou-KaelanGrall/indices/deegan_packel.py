from __future__ import annotations

from core.games import WeightedVotingGame


def deegan_packel(game: WeightedVotingGame) -> dict[int, float]:
    """
    Indice de Deegan-Packel (1978) : les coalitions gagnantes minimales sont
    supposees equiprobables et partagent le pouvoir a parts egales, soit
    DP_i = (1/|M|) * somme des 1/|S| sur les coalitions minimales contenant i.
    """
    power = {i: 0.0 for i in game.players}
    mwcs = game.minimal_winning_coalitions()

    for coalition in mwcs:
        share = 1.0 / len(coalition)
        for player in coalition:
            power[player] += share

    return {i: power[i] / len(mwcs) for i in game.players}
