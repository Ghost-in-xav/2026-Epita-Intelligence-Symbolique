from __future__ import annotations

import time
from dataclasses import dataclass

import pandas as pd

from core.games import WeightedVotingGame
from formal.smt_encoding import count_swings_smt, enumerate_minimal_winning_smt
from indices.banzhaf import banzhaf_normalized, swing_counts
from indices.deegan_packel import deegan_packel
from indices.shapley_shubik import shapley_shubik_exact, shapley_shubik_monte_carlo


@dataclass(frozen=True)
class IndexBundle:
    shapley_shubik: dict[int, float]
    banzhaf_normalized: dict[int, float]
    deegan_packel: dict[int, float]


def compute_all_indices(game: WeightedVotingGame) -> IndexBundle:
    return IndexBundle(
        shapley_shubik=shapley_shubik_exact(game),
        banzhaf_normalized=banzhaf_normalized(game),
        deegan_packel=deegan_packel(game),
    )


def comparison_table(game: WeightedVotingGame) -> pd.DataFrame:
    """Tableau sieges / indices en pourcentages, trie par sieges decroissants."""
    bundle = compute_all_indices(game)
    total = game.total_weight

    rows = []
    for i in game.players:
        seat_share = game.weights[i] / total
        ss = bundle.shapley_shubik[i]
        rows.append(
            {
                "Groupe": game.names[i],
                "Sieges": game.weights[i],
                "Part sieges %": round(seat_share * 100, 2),
                "Shapley-Shubik %": round(ss * 100, 2),
                "Banzhaf %": round(bundle.banzhaf_normalized[i] * 100, 2),
                "Deegan-Packel %": round(bundle.deegan_packel[i] * 100, 2),
                "Ecart SS-sieges (pts)": round((ss - seat_share) * 100, 2),
            }
        )

    df = pd.DataFrame(rows)
    return df.sort_values("Sieges", ascending=False).reset_index(drop=True)


def montecarlo_benchmark(
    game: WeightedVotingGame,
    samples: tuple[int, ...] = (1_000, 10_000, 100_000),
    seed: int = 42,
) -> pd.DataFrame:
    """Erreur maximale et temps du Monte Carlo face au calcul exact."""
    t0 = time.perf_counter()
    exact = shapley_shubik_exact(game)
    exact_ms = (time.perf_counter() - t0) * 1000

    rows = [
        {
            "Methode": "Exact",
            "Echantillons": "-",
            "Erreur max": 0.0,
            "Temps (ms)": round(exact_ms, 1),
        }
    ]

    for n_samples in samples:
        t0 = time.perf_counter()
        approx = shapley_shubik_monte_carlo(game, n_samples=n_samples, seed=seed)
        ms = (time.perf_counter() - t0) * 1000
        max_err = max(abs(approx[i] - exact[i]) for i in game.players)
        rows.append(
            {
                "Methode": "Monte Carlo",
                "Echantillons": n_samples,
                "Erreur max": round(max_err, 5),
                "Temps (ms)": round(ms, 1),
            }
        )

    return pd.DataFrame(rows)


def cross_validate_smt(game: WeightedVotingGame) -> dict[str, bool]:
    """
    Concordance entre enumeration combinatoire et encodage SMT :
    memes decomptes de swings, memes coalitions gagnantes minimales.
    """
    combinatorial_swings = swing_counts(game)
    smt_swings = {i: count_swings_smt(game, i) for i in game.players}

    combinatorial_mwc = {frozenset(c) for c in game.minimal_winning_coalitions()}
    smt_mwc = set(enumerate_minimal_winning_smt(game))

    return {
        "swings_match": combinatorial_swings == smt_swings,
        "mwc_match": combinatorial_mwc == smt_mwc,
    }


def player_status_table(game: WeightedVotingGame) -> pd.DataFrame:
    """Statut de chaque joueur : veto, nul, dictateur."""
    rows = []
    for i in game.players:
        rows.append(
            {
                "Groupe": game.names[i],
                "Sieges": game.weights[i],
                "Veto": game.is_veto(i),
                "Nul (dummy)": game.is_dummy(i),
                "Dictateur": game.is_dictator(i),
            }
        )
    return pd.DataFrame(rows)
