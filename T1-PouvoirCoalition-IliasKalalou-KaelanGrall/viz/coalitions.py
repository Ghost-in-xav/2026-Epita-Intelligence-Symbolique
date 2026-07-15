from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from core.games import WeightedVotingGame


def plot_minimal_winning_matrix(
    game: WeightedVotingGame,
    max_coalitions: int = 40,
) -> Figure:
    """Matrice d'appartenance des MWC : une ligne par coalition, une colonne par joueur."""
    mwcs = sorted(game.minimal_winning_coalitions(), key=len)
    fig, ax = plt.subplots(
        figsize=(max(6, game.n_players * 0.8), max(3, len(mwcs) * 0.3))
    )

    if not mwcs:
        ax.text(0.5, 0.5, "Aucune coalition gagnante minimale", ha="center", va="center")
        ax.axis("off")
        return fig

    shown = mwcs[:max_coalitions]
    matrix = np.zeros((len(shown), game.n_players))
    for row, coalition in enumerate(shown):
        for player in coalition:
            matrix[row, player] = 1.0

    ax.imshow(matrix, aspect="auto", cmap="Greens", vmin=0, vmax=1)
    ax.set_xticks(range(game.n_players))
    ax.set_xticklabels([game.names[i] for i in game.players], rotation=45, ha="right")
    ax.set_yticks(range(len(shown)))
    ax.set_yticklabels([f"MWC {i + 1}" for i in range(len(shown))])
    ax.set_title(
        f"Coalitions gagnantes minimales ({len(mwcs)} au total, {len(shown)} affichees)"
    )
    fig.tight_layout()
    return fig


def plot_critical_frequency(
    game: WeightedVotingGame,
    swing_counts: dict[int, int],
) -> Figure:
    """Nombre de coalitions ou chaque joueur est critique (eta_i), trie decroissant."""
    ordered = sorted(game.players, key=lambda i: swing_counts[i], reverse=True)
    labels = [game.names[i] for i in ordered]
    values = [swing_counts[i] for i in ordered]

    fig, ax = plt.subplots(figsize=(max(8, len(ordered) * 0.9), 5))
    ax.bar(labels, values, color="#ff7f0e")
    ax.set_ylabel("Nombre de coalitions critiques (eta_i)")
    ax.set_title("Frequence de criticite par joueur")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    return fig
