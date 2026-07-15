from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.figure import Figure


def plot_dhondt_quotients(
    votes: dict[str, int],
    allocation: dict[str, int],
    max_rows: int = 8,
) -> Figure:
    """Quotients voix / k par parti ; point plein = siege attribue."""
    fig, ax = plt.subplots(figsize=(max(8, len(votes) * 1.1), 5))

    for code, v in votes.items():
        seats = allocation.get(code, 0)
        ks = range(1, max_rows + 1)
        quotients = [v / k for k in ks]
        filled = [k <= seats for k in ks]
        ax.scatter(
            [code] * max_rows,
            quotients,
            facecolors=["#1f77b4" if f else "none" for f in filled],
            edgecolors="#1f77b4",
            s=60,
        )

    ax.set_ylabel("Quotient voix / k")
    ax.set_title("Quotients D'Hondt (plein = siege attribue, creux = non attribue)")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    return fig


def plot_seats_bar(allocation: dict[str, int], title: str = "Sieges attribues (D'Hondt)") -> Figure:
    """Sieges attribues par parti, tries par nombre decroissant."""
    ordered = sorted(allocation, key=lambda c: allocation[c], reverse=True)
    values = [allocation[c] for c in ordered]

    fig, ax = plt.subplots(figsize=(max(7, len(ordered) * 0.9), 4.5))
    ax.bar(ordered, values, color="#1f77b4")
    ax.set_ylabel("Sieges")
    ax.set_title(title)
    for i, v in enumerate(values):
        ax.text(i, v + 0.3, str(v), ha="center", fontsize=9)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    fig.tight_layout()
    return fig
