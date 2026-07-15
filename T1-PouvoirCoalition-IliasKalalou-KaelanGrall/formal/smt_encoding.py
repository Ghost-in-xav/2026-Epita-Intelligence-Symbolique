from __future__ import annotations

import z3

from core.games import WeightedVotingGame


def _membership_vars(game: WeightedVotingGame) -> list[z3.BoolRef]:
    """Une variable booleenne x_i par joueur : i appartient ou non a la coalition."""
    return [z3.Bool(f"x_{i}") for i in game.players]


def _coalition_weight_expr(game: WeightedVotingGame, x: list[z3.BoolRef]) -> z3.ArithRef:
    """Poids de la coalition : somme des w_i pour les x_i vrais."""
    return z3.Sum([z3.If(x[i], game.weights[i], 0) for i in game.players])


def is_veto_smt(game: WeightedVotingGame, player: int) -> bool:
    """Veto si Z3 repond UNSAT : aucune coalition gagnante sans le joueur."""
    x = _membership_vars(game)
    solver = z3.Solver()
    solver.add(z3.Not(x[player]))
    solver.add(_coalition_weight_expr(game, x) >= game.quota)
    return solver.check() == z3.unsat


def is_dummy_smt(game: WeightedVotingGame, player: int) -> bool:
    """Joueur nul si Z3 repond UNSAT : aucune coalition que son arrivee fait gagner."""
    x = _membership_vars(game)
    weight_without = _coalition_weight_expr(game, x)
    solver = z3.Solver()
    solver.add(z3.Not(x[player]))
    solver.add(weight_without < game.quota)
    solver.add(weight_without + game.weights[player] >= game.quota)
    return solver.check() == z3.unsat


def is_dictator_smt(game: WeightedVotingGame, player: int) -> bool:
    """Le joueur gagne seul et aucune coalition sans lui ne gagne."""
    if game.weights[player] < game.quota:
        return False
    return is_veto_smt(game, player)


def swings_by_size_smt(game: WeightedVotingGame, player: int) -> dict[int, int]:
    """
    Enumere par modeles Z3 les coalitions ou le joueur est critique et les
    compte par taille, information necessaire a la ponderation de Shapley-Shubik.
    """
    others = [p for p in game.players if p != player]
    x = {p: z3.Bool(f"x_{p}") for p in others}
    weight_without = z3.Sum([z3.If(x[p], game.weights[p], 0) for p in others])

    solver = z3.Solver()
    solver.add(weight_without < game.quota)
    solver.add(weight_without + game.weights[player] >= game.quota)

    counts: dict[int, int] = {}
    while solver.check() == z3.sat:
        model = solver.model()
        present = {p: bool(model.eval(x[p], model_completion=True)) for p in others}
        size = sum(present.values())
        counts[size] = counts.get(size, 0) + 1
        # Bloque le modele courant pour passer au suivant.
        solver.add(z3.Or([x[p] != present[p] for p in others]))

    return counts


def count_swings_smt(game: WeightedVotingGame, player: int) -> int:
    """Nombre total de coalitions ou le joueur est critique, par la voie SMT."""
    return sum(swings_by_size_smt(game, player).values())


def enumerate_minimal_winning_smt(game: WeightedVotingGame) -> list[frozenset[int]]:
    """Enumere les coalitions gagnantes minimales par contraintes SMT."""
    x = _membership_vars(game)
    weight = _coalition_weight_expr(game, x)

    solver = z3.Solver()
    solver.add(weight >= game.quota)
    # Minimalite : tout membre present est critique.
    for i in game.players:
        solver.add(z3.Implies(x[i], weight - game.weights[i] < game.quota))

    coalitions: list[frozenset[int]] = []
    while solver.check() == z3.sat:
        model = solver.model()
        present = frozenset(
            i for i in game.players if bool(model.eval(x[i], model_completion=True))
        )
        coalitions.append(present)
        solver.add(z3.Or([x[i] != (i in present) for i in game.players]))

    return coalitions
