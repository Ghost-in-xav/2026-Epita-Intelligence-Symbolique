from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations

import z3


@dataclass(frozen=True)
class AxiomResult:
    """Resultat d'une preuve d'axiome : proved est vrai si la negation est UNSAT."""

    axiom: str
    n_players: int
    proved: bool
    detail: str


def _all_subsets(players: Sequence[int]) -> list[frozenset[int]]:
    subsets: list[frozenset[int]] = []
    for size in range(len(players) + 1):
        for combo in combinations(players, size):
            subsets.append(frozenset(combo))
    return subsets


def _value_vars(prefix: str, subsets: list[frozenset[int]]) -> dict[frozenset[int], z3.ArithRef]:
    return {s: z3.Real(f"{prefix}_{sorted(s)}") for s in subsets}


def _simple_game_constraints(
    v: dict[frozenset[int], z3.ArithRef],
    players: Sequence[int],
) -> list[z3.BoolRef]:
    """v(vide) = 0, v(N) = 1, valeurs dans {0, 1}, monotonie."""
    full = frozenset(players)
    constraints: list[z3.BoolRef] = [v[frozenset()] == 0, v[full] == 1]
    for var in v.values():
        constraints.append(z3.Or(var == 0, var == 1))
    for s in v:
        for i in players:
            if i not in s:
                constraints.append(v[s] <= v[s | {i}])
    return constraints


def _shapley_expr(
    v: dict[frozenset[int], z3.ArithRef],
    player: int,
    players: Sequence[int],
) -> z3.ArithRef:
    """phi_i = somme sur S sans i de |S|!(n-|S|-1)!/n! * (v(S+i) - v(S))."""
    n = len(players)
    factorial_n = math.factorial(n)
    terms: list[z3.ArithRef] = []
    others = [p for p in players if p != player]
    for size in range(len(others) + 1):
        coeff = z3.RealVal(math.factorial(size) * math.factorial(n - size - 1)) / factorial_n
        for combo in combinations(others, size):
            s = frozenset(combo)
            terms.append(coeff * (v[s | {player}] - v[s]))
    return z3.Sum(terms) if terms else z3.RealVal(0)


def _banzhaf_absolute_expr(
    v: dict[frozenset[int], z3.ArithRef],
    player: int,
    players: Sequence[int],
) -> z3.ArithRef:
    """psi_i = (1/2^(n-1)) * somme sur S sans i de (v(S+i) - v(S))."""
    n = len(players)
    denom = z3.RealVal(2 ** (n - 1))
    others = [p for p in players if p != player]
    terms: list[z3.ArithRef] = []
    for size in range(len(others) + 1):
        for combo in combinations(others, size):
            s = frozenset(combo)
            terms.append(v[s | {player}] - v[s])
    return (z3.Sum(terms) if terms else z3.RealVal(0)) / denom


def prove_banzhaf_symmetry(n_players: int) -> AxiomResult:
    """L'indice de Banzhaf satisfait la symetrie : negation UNSAT attendue."""
    if n_players < 2:
        return AxiomResult("Banzhaf symetrie", n_players, False, "Au moins deux joueurs requis.")

    players = range(n_players)
    subsets = _all_subsets(players)
    v = _value_vars("v", subsets)

    solver = z3.Solver()
    solver.add(_simple_game_constraints(v, players))
    for s in subsets:
        if 0 not in s and 1 not in s:
            solver.add(v[s | {0}] == v[s | {1}])
    solver.add(_banzhaf_absolute_expr(v, 0, players) != _banzhaf_absolute_expr(v, 1, players))

    proved = solver.check() == z3.unsat
    detail = "Negation UNSAT : Banzhaf satisfait la symetrie." if proved else "Statut inattendu."
    return AxiomResult("Banzhaf symetrie", n_players, proved, detail)


def prove_banzhaf_null_player(n_players: int) -> AxiomResult:
    """L'indice de Banzhaf satisfait l'axiome du joueur nul : negation UNSAT."""
    players = range(n_players)
    subsets = _all_subsets(players)
    v = _value_vars("v", subsets)

    solver = z3.Solver()
    solver.add(_simple_game_constraints(v, players))
    for s in subsets:
        if 0 not in s:
            solver.add(v[s | {0}] == v[s])
    solver.add(_banzhaf_absolute_expr(v, 0, players) != 0)

    proved = solver.check() == z3.unsat
    detail = "Negation UNSAT : Banzhaf satisfait le joueur nul." if proved else "Statut inattendu."
    return AxiomResult("Banzhaf joueur nul", n_players, proved, detail)


def refute_banzhaf_efficiency(n_players: int) -> AxiomResult:
    """
    L'indice de Banzhaf ne satisfait pas l'efficacite : Z3 exhibe un jeu simple
    ou la somme des indices differe de v(N). C'est la propriete qui distingue
    Banzhaf de Shapley-Shubik. Le contre-exemple apparait des n = 3.
    """
    players = range(n_players)
    subsets = _all_subsets(players)
    v = _value_vars("v", subsets)

    solver = z3.Solver()
    solver.add(_simple_game_constraints(v, players))
    total = z3.Sum([_banzhaf_absolute_expr(v, i, players) for i in players])
    solver.add(total != v[frozenset(players)])

    refuted = solver.check() == z3.sat
    detail = (
        "SAT : Z3 exhibe un jeu ou la somme des indices de Banzhaf differe de v(N)."
        if refuted
        else "Aucun contre-exemple a ce n (Banzhaf y coincide avec l'efficacite)."
    )
    return AxiomResult("Banzhaf efficacite (refutee)", n_players, refuted, detail)


def prove_efficiency(n_players: int) -> AxiomResult:
    """Efficacite : somme des phi_i = v(N)."""
    players = range(n_players)
    subsets = _all_subsets(players)
    v = _value_vars("v", subsets)

    solver = z3.Solver()
    solver.add(_simple_game_constraints(v, players))
    total = z3.Sum([_shapley_expr(v, i, players) for i in players])
    solver.add(total != v[frozenset(players)])

    status = solver.check()
    proved = status == z3.unsat
    detail = "Negation UNSAT : efficacite demontree." if proved else f"Statut Z3 inattendu : {status}."
    return AxiomResult("Efficacite", n_players, proved, detail)


def prove_null_player(n_players: int) -> AxiomResult:
    """Joueur nul : si v(S + 0) = v(S) pour tout S, alors phi_0 = 0."""
    players = range(n_players)
    subsets = _all_subsets(players)
    v = _value_vars("v", subsets)

    solver = z3.Solver()
    solver.add(_simple_game_constraints(v, players))
    for s in subsets:
        if 0 not in s:
            solver.add(v[s | {0}] == v[s])
    solver.add(_shapley_expr(v, 0, players) != 0)

    status = solver.check()
    proved = status == z3.unsat
    detail = "Negation UNSAT : joueur nul demontre." if proved else f"Statut Z3 inattendu : {status}."
    return AxiomResult("Joueur nul", n_players, proved, detail)


def prove_symmetry(n_players: int) -> AxiomResult:
    """Symetrie : si 0 et 1 sont interchangeables, alors phi_0 = phi_1."""
    if n_players < 2:
        return AxiomResult("Symetrie", n_players, False, "Au moins deux joueurs requis.")

    players = range(n_players)
    subsets = _all_subsets(players)
    v = _value_vars("v", subsets)

    solver = z3.Solver()
    solver.add(_simple_game_constraints(v, players))
    for s in subsets:
        if 0 not in s and 1 not in s:
            solver.add(v[s | {0}] == v[s | {1}])
    solver.add(_shapley_expr(v, 0, players) != _shapley_expr(v, 1, players))

    status = solver.check()
    proved = status == z3.unsat
    detail = "Negation UNSAT : symetrie demontree." if proved else f"Statut Z3 inattendu : {status}."
    return AxiomResult("Symetrie", n_players, proved, detail)


def prove_additivity(n_players: int) -> AxiomResult:
    """Additivite : phi_0(v + w) = phi_0(v) + phi_0(w), identite lineaire sur reels libres."""
    players = range(n_players)
    subsets = _all_subsets(players)
    v = _value_vars("v", subsets)
    w = _value_vars("w", subsets)
    vw = {s: v[s] + w[s] for s in subsets}

    solver = z3.Solver()
    solver.add(v[frozenset()] == 0, w[frozenset()] == 0)
    phi_sum = _shapley_expr(v, 0, players) + _shapley_expr(w, 0, players)
    solver.add(_shapley_expr(vw, 0, players) != phi_sum)

    status = solver.check()
    proved = status == z3.unsat
    detail = "Negation UNSAT : additivite demontree." if proved else f"Statut Z3 inattendu : {status}."
    return AxiomResult("Additivite", n_players, proved, detail)


def _is_minimal_winning_expr(
    v: dict[frozenset[int], z3.ArithRef],
    subset: frozenset[int],
) -> z3.BoolRef:
    """
    Predicat Z3 : le sous-ensemble est une coalition gagnante minimale. Il gagne
    (v(S) = 1) et le retrait de n'importe lequel de ses membres le fait perdre
    (v(S - i) = 0). La coalition vide n'est jamais gagnante minimale.
    """
    if not subset:
        return z3.BoolVal(False)
    conditions: list[z3.BoolRef] = [v[subset] == 1]
    for i in subset:
        conditions.append(v[subset - {i}] == 0)
    return z3.And(conditions)


def _deegan_packel_numerator(
    v: dict[frozenset[int], z3.ArithRef],
    player: int,
    subsets: list[frozenset[int]],
) -> z3.ArithRef:
    """
    Numerateur non normalise de Deegan-Packel : somme des 1/|S| sur les
    coalitions gagnantes minimales contenant le joueur. Le denominateur commun
    (nombre de coalitions gagnantes minimales) est volontairement ecarte, ce qui
    evite toute division par une variable et garde la preuve dans l'arithmetique
    lineaire decidable par Z3.
    """
    terms: list[z3.ArithRef] = []
    for s in subsets:
        if player in s:
            share = z3.RealVal(1) / z3.RealVal(len(s))
            terms.append(z3.If(_is_minimal_winning_expr(v, s), share, z3.RealVal(0)))
    return z3.Sum(terms) if terms else z3.RealVal(0)


def _mwc_count_expr(
    v: dict[frozenset[int], z3.ArithRef],
    subsets: list[frozenset[int]],
) -> z3.ArithRef:
    """Nombre de coalitions gagnantes minimales, comme expression Z3."""
    terms = [z3.If(_is_minimal_winning_expr(v, s), z3.RealVal(1), z3.RealVal(0)) for s in subsets]
    return z3.Sum(terms) if terms else z3.RealVal(0)


def prove_deegan_packel_symmetry(n_players: int) -> AxiomResult:
    """
    L'indice de Deegan-Packel satisfait la symetrie. Deux joueurs interchangeables
    ont le meme numerateur ; le denominateur (nombre de coalitions minimales) leur
    etant commun, l'egalite des numerateurs entraine l'egalite des indices. On
    prouve donc l'egalite des numerateurs par UNSAT de sa negation.
    """
    if n_players < 2:
        return AxiomResult("Deegan-Packel symetrie", n_players, False, "Au moins deux joueurs requis.")

    players = range(n_players)
    subsets = _all_subsets(players)
    v = _value_vars("v", subsets)

    solver = z3.Solver()
    solver.add(_simple_game_constraints(v, players))
    for s in subsets:
        if 0 not in s and 1 not in s:
            solver.add(v[s | {0}] == v[s | {1}])
    solver.add(_deegan_packel_numerator(v, 0, subsets) != _deegan_packel_numerator(v, 1, subsets))

    proved = solver.check() == z3.unsat
    detail = (
        "Negation UNSAT : Deegan-Packel satisfait la symetrie (numerateurs egaux)."
        if proved
        else "Statut inattendu."
    )
    return AxiomResult("Deegan-Packel symetrie", n_players, proved, detail)


def prove_deegan_packel_null_player(n_players: int) -> AxiomResult:
    """
    L'indice de Deegan-Packel satisfait l'axiome du joueur nul. Un joueur nul
    n'appartient a aucune coalition gagnante minimale, donc son numerateur est
    nul et son indice aussi. On prouve numerateur = 0 par UNSAT de sa negation.
    """
    players = range(n_players)
    subsets = _all_subsets(players)
    v = _value_vars("v", subsets)

    solver = z3.Solver()
    solver.add(_simple_game_constraints(v, players))
    for s in subsets:
        if 0 not in s:
            solver.add(v[s | {0}] == v[s])
    solver.add(_deegan_packel_numerator(v, 0, subsets) != 0)

    proved = solver.check() == z3.unsat
    detail = (
        "Negation UNSAT : Deegan-Packel satisfait le joueur nul (numerateur nul)."
        if proved
        else "Statut inattendu."
    )
    return AxiomResult("Deegan-Packel joueur nul", n_players, proved, detail)


def prove_deegan_packel_efficiency(n_players: int) -> AxiomResult:
    """
    L'indice de Deegan-Packel satisfait l'efficacite : la somme des indices vaut 1.
    Deux faits sont etablis par Z3. D'abord la somme des numerateurs egale le
    nombre de coalitions gagnantes minimales (chaque coalition minimale distribue
    exactement une unite entre ses membres). Ensuite tout jeu simple possede au
    moins une coalition gagnante minimale, donc le denominateur est non nul et la
    somme normalisee vaut 1. Chaque fait est prouve par UNSAT de sa negation.
    """
    players = range(n_players)
    subsets = _all_subsets(players)
    v = _value_vars("v", subsets)

    total_numerator = z3.Sum([_deegan_packel_numerator(v, i, subsets) for i in players])
    count = _mwc_count_expr(v, subsets)

    identity_solver = z3.Solver()
    identity_solver.add(_simple_game_constraints(v, players))
    identity_solver.add(total_numerator != count)
    identity = identity_solver.check() == z3.unsat

    nonempty_solver = z3.Solver()
    nonempty_solver.add(_simple_game_constraints(v, players))
    nonempty_solver.add(count < 1)
    nonempty = nonempty_solver.check() == z3.unsat

    proved = identity and nonempty
    detail = (
        "Negation UNSAT : somme des numerateurs = nombre de coalitions minimales (>= 1), donc somme des indices = 1."
        if proved
        else "Statut inattendu."
    )
    return AxiomResult("Deegan-Packel efficacite", n_players, proved, detail)


def prove_all_deegan_packel_axioms(n_players: int) -> list[AxiomResult]:
    """
    Preuves Z3 des axiomes applicables a Deegan-Packel : symetrie, joueur nul et
    efficacite. L'additivite n'est pas definie pour un indice de jeux simples (la
    somme de deux jeux simples n'est pas un jeu simple), comme pour tout indice de
    pouvoir a priori. L'encodage repose sur le predicat de coalition gagnante
    minimale, l'indice etant non lineaire en les valeurs des coalitions.
    """
    return [
        prove_deegan_packel_symmetry(n_players),
        prove_deegan_packel_null_player(n_players),
        prove_deegan_packel_efficiency(n_players),
    ]


def prove_all_axioms(n_players: int) -> list[AxiomResult]:
    """
    Verifie les quatre axiomes de Shapley-Shubik pour n joueurs : les 2^n
    valeurs v(S) deviennent des variables reelles Z3 et chaque axiome est
    demontre en etablissant que sa negation est UNSAT. Preuve bornee, valable
    pour le n teste (Tang et Lin 2009).
    """
    return [
        prove_efficiency(n_players),
        prove_null_player(n_players),
        prove_symmetry(n_players),
        prove_additivity(n_players),
    ]
