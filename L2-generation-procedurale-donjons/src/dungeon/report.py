"""Agregation du CSV de benchmark en tableaux markdown et graphiques comparatifs."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def generate_report(df: pd.DataFrame, out_md: Path, plots_dir: Path) -> str:
    plots_dir.mkdir(parents=True, exist_ok=True)

    summary = (
        df.groupby(["method", "size"])
        .agg(
            elapsed_s_mean=("elapsed_s", "mean"),
            connectivity_mean=("connectivity_ratio", "mean"),
            fully_connected_rate=("is_fully_connected", "mean"),
            path_length_mean=("path_length", "mean"),
            density_mean=("floor_density", "mean"),
            room_variety_mean=("room_size_variety", "mean"),
            n_attempts_mean=("n_attempts", "mean"),
        )
        .round(3)
        .reset_index()
    )

    _plot_bar(df, "elapsed_s", "Temps de generation (s)", plots_dir / "elapsed_s.png")
    _plot_bar(df, "connectivity_ratio", "Ratio de connectivite", plots_dir / "connectivity_ratio.png")
    _plot_bar(df, "path_length", "Longueur du chemin start->end", plots_dir / "path_length.png")

    lines = [
        "# Rapport comparatif CP-SAT vs WFC — generation procedurale de donjons",
        "",
        "## Synthese par methode et taille",
        "",
        summary.to_markdown(index=False),
        "",
        "## Graphiques",
        "",
        "![Temps de generation](plots/elapsed_s.png)",
        "",
        "![Connectivite](plots/connectivity_ratio.png)",
        "",
        "![Longueur de chemin](plots/path_length.png)",
        "",
    ]
    report_text = "\n".join(lines)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(report_text, encoding="utf-8")
    return report_text


def _plot_bar(df: pd.DataFrame, column: str, title: str, out_path: Path) -> None:
    pivot = df.groupby(["size", "method"])[column].mean().unstack("method")
    ax = pivot.plot(kind="bar", figsize=(6, 4), title=title)
    ax.set_xlabel("taille de grille")
    ax.set_ylabel(column)
    plt.tight_layout()
    plt.savefig(out_path, dpi=120)
    plt.close()
