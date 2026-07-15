from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from core.games import WeightedVotingGame


def plot_power_vs_weight(
    game: WeightedVotingGame,
    shapley: dict[int, float],
    banzhaf: dict[int, float],
    deegan: dict[int, float],
    title: str = "Pouvoir de vote contre part de sieges",
) -> Figure:
    """Barres groupees : part de sieges et les trois indices, par joueur."""
    players = list(game.players)
    labels = [game.names[i] for i in players]
    total_weight = game.total_weight

    seat_share = [game.weights[i] / total_weight for i in players]
    ss = [shapley[i] for i in players]
    bz = [banzhaf[i] for i in players]
    dp = [deegan[i] for i in players]

    x = np.arange(len(players))
    width = 0.2

    fig, ax = plt.subplots(figsize=(max(8, len(players) * 0.9), 5))
    ax.bar(x - 1.5 * width, seat_share, width, label="Part de sieges", color="#9aa0a6")
    ax.bar(x - 0.5 * width, ss, width, label="Shapley-Shubik", color="#1f77b4")
    ax.bar(x + 0.5 * width, bz, width, label="Banzhaf", color="#ff7f0e")
    ax.bar(x + 1.5 * width, dp, width, label="Deegan-Packel", color="#2ca02c")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("Part (fraction du total)")
    ax.set_title(title)
    ax.legend()
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    return fig


def plot_power_gap(
    game: WeightedVotingGame,
    power: dict[int, float],
    index_name: str = "Shapley-Shubik",
) -> Figure:
    """Ecart pouvoir moins part de sieges, trie ; positif = pouvoir superieur au poids."""
    total_weight = game.total_weight
    gaps = {i: power[i] - game.weights[i] / total_weight for i in game.players}
    ordered = sorted(game.players, key=lambda i: gaps[i])
    labels = [game.names[i] for i in ordered]
    values = [gaps[i] * 100 for i in ordered]
    colors = ["#d62728" if v < 0 else "#2ca02c" for v in values]

    fig, ax = plt.subplots(figsize=(max(8, len(ordered) * 0.9), 5))
    ax.bar(labels, values, color=colors)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Ecart pouvoir - sieges (points de %)")
    ax.set_title(f"Ecart entre pouvoir {index_name} et part de sieges")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    return fig
