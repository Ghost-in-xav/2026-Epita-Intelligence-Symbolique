from __future__ import annotations

from itertools import combinations

from core.games import WeightedVotingGame
from formal.axioms import (
    prove_additivity,
    prove_banzhaf_null_player,
    prove_banzhaf_symmetry,
    prove_deegan_packel_efficiency,
    prove_deegan_packel_null_player,
    prove_deegan_packel_symmetry,
    prove_efficiency,
    prove_null_player,
    prove_symmetry,
    refute_banzhaf_efficiency,
)

_EMPIRICAL_GAMES = [
    WeightedVotingGame((2, 1, 1), 3),
    WeightedVotingGame((3, 2, 1), 4),
    WeightedVotingGame((5, 3, 2, 1), 6),
    WeightedVotingGame((4, 4, 2, 1), 6),
]


def _swap_players(weights: tuple[int, ...], i: int, j: int) -> tuple[int, ...]:
    w = list(weights)
    w[i], w[j] = w[j], w[i]
    return tuple(w)


def _satisfies_symmetry_and_null(index) -> bool:
    """
    Verifie empiriquement qu'un indice donne un pouvoir egal a deux joueurs de
    meme poids et un pouvoir nul a un joueur nul, sur une batterie de jeux.
    """
    for game in _EMPIRICAL_GAMES:
        values = index(game)
        for i in range(game.n_players):
            for j in range(i + 1, game.n_players):
                if game.weights[i] == game.weights[j] and abs(values[i] - values[j]) > 1e-9:
                    return False
            if game.is_dummy(i) and abs(values[i]) > 1e-9:
                return False
    return True


def banzhaf_additivity_counterexample() -> dict[str, float]:
    """
    Contre-exemple explicite : l'indice de Banzhaf normalise n'est pas additif.
    Sur les jeux v = [2 ; 1,1,1] et w = [3 ; 1,1,1], on compare beta(v+w) a
    beta(v) + beta(w) pour le joueur 0 ; l'egalite de l'additivite est violee.
    """
    def banzhaf_normalized_general(vfun, n: int) -> dict[int, float]:
        eta = {i: 0.0 for i in range(n)}
        for i in range(n):
            others = [p for p in range(n) if p != i]
            for size in range(len(others) + 1):
                for combo in combinations(others, size):
                    s = frozenset(combo)
                    eta[i] += vfun(s | {i}) - vfun(s)
        total = sum(eta.values())
        return {i: eta[i] / total for i in range(n)}

    def v(s: frozenset[int]) -> float:
        return 1.0 if len(s) >= 2 else 0.0

    def w(s: frozenset[int]) -> float:
        return 1.0 if len(s) >= 3 else 0.0

    def vw(s: frozenset[int]) -> float:
        return v(s) + w(s)

    bv = banzhaf_normalized_general(v, 3)
    bw = banzhaf_normalized_general(w, 3)
    bvw = banzhaf_normalized_general(vw, 3)
    return {
        "beta(v)_0": bv[0],
        "beta(w)_0": bw[0],
        "beta(v)+beta(w)": bv[0] + bw[0],
        "beta(v+w)_0": bvw[0],
    }


def axiom_matrix(n_players: int = 4) -> list[dict[str, str]]:
    """
    Grille indice x axiome resumant quelle propriete chaque indice satisfait et
    par quelle methode. Fait apparaitre ce qui distingue les indices : seul
    Shapley-Shubik concilie efficacite et additivite, tandis que Banzhaf doit
    sacrifier l'une ou l'autre selon sa normalisation.
    """
    yes = "satisfait"
    no = "viole"

    eff_shapley = prove_efficiency(n_players).proved
    add_shapley = prove_additivity(n_players).proved
    sym_shapley = prove_symmetry(n_players).proved
    null_shapley = prove_null_player(n_players).proved

    sym_banzhaf = prove_banzhaf_symmetry(n_players).proved
    null_banzhaf = prove_banzhaf_null_player(n_players).proved
    eff_banzhaf_refuted = refute_banzhaf_efficiency(max(n_players, 3)).proved

    sym_dp = prove_deegan_packel_symmetry(n_players).proved
    null_dp = prove_deegan_packel_null_player(n_players).proved
    eff_dp = prove_deegan_packel_efficiency(n_players).proved

    ce = banzhaf_additivity_counterexample()
    banzhaf_norm_additive = abs(ce["beta(v+w)_0"] - ce["beta(v)+beta(w)"]) < 1e-9

    return [
        {
            "Axiome": "Symetrie",
            "Shapley-Shubik": f"{yes} (preuve Z3)" if sym_shapley else no,
            "Banzhaf": f"{yes} (preuve Z3)" if sym_banzhaf else no,
            "Deegan-Packel": f"{yes} (preuve Z3)" if sym_dp else no,
        },
        {
            "Axiome": "Joueur nul",
            "Shapley-Shubik": f"{yes} (preuve Z3)" if null_shapley else no,
            "Banzhaf": f"{yes} (preuve Z3)" if null_banzhaf else no,
            "Deegan-Packel": f"{yes} (preuve Z3)" if null_dp else no,
        },
        {
            "Axiome": "Efficacite (somme = 1)",
            "Shapley-Shubik": f"{yes} (preuve Z3)" if eff_shapley else no,
            "Banzhaf": f"{no} (contre-exemple Z3)" if eff_banzhaf_refuted else yes,
            "Deegan-Packel": f"{yes} (preuve Z3)" if eff_dp else no,
        },
        {
            "Axiome": "Additivite",
            "Shapley-Shubik": f"{yes} (preuve Z3)" if add_shapley else no,
            "Banzhaf": f"{no} (contre-exemple)" if not banzhaf_norm_additive else yes,
            "Deegan-Packel": "non defini (indice sur jeux simples)",
        },
    ]
