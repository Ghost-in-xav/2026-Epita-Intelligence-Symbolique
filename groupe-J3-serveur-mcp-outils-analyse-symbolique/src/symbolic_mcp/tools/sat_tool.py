"""Outil SAT — resolution de satisfiabilite booleenne (CNF) via PySAT.

Le probleme est fourni en forme normale conjonctive (CNF) au format DIMACS :
une liste de clauses, chaque clause etant une liste d'entiers non nuls.
Un entier `i > 0` designe le litteral positif de la variable `i` ; `-i` designe
sa negation. Les variables sont indexees a partir de 1.

Exemple : (a OR b) AND (NOT a OR c) AND (NOT b)
    clauses = [[1, 2], [-1, 3], [-2]]   avec var_names = {1: "a", 2: "b", 3: "c"}
"""

from __future__ import annotations

from typing import Any

from pysat.solvers import Glucose3


def _normalize_var_names(var_names: dict | None) -> dict[int, str]:
    """Accepte des cles int OU str (JSON transforme les cles en str)."""
    if not var_names:
        return {}
    out: dict[int, str] = {}
    for k, v in var_names.items():
        try:
            out[int(k)] = str(v)
        except (TypeError, ValueError):
            continue
    return out


def solve_sat(
    clauses: list[list[int]],
    assumptions: list[int] | None = None,
    var_names: dict | None = None,
    max_models: int = 1,
) -> dict[str, Any]:
    """Resout un probleme SAT en CNF (DIMACS) et renvoie le(s) modele(s).

    Args:
        clauses: liste de clauses ; chaque clause est une liste de litteraux
            entiers non nuls (positif = variable vraie, negatif = variable fausse).
        assumptions: litteraux supposes vrais le temps de la resolution (optionnel).
        var_names: correspondance {index_variable: nom_lisible} pour un modele
            interpretable (optionnel).
        max_models: nombre maximum de modeles distincts a enumerer (defaut 1).

    Returns:
        dict avec `status` = "SAT" | "UNSAT", et si SAT la liste des modeles
        (affectations booleennes), plus un `summary` en langage naturel.
    """
    if not isinstance(clauses, list) or not clauses:
        return {
            "ok": False,
            "tool": "sat_solve",
            "error": "Le champ 'clauses' doit etre une liste non vide de clauses.",
        }
    for cl in clauses:
        if not isinstance(cl, list) or any((not isinstance(x, int)) or x == 0 for x in cl):
            return {
                "ok": False,
                "tool": "sat_solve",
                "error": f"Clause invalide {cl!r} : liste d'entiers non nuls attendue.",
            }
    if assumptions is not None and (
        not isinstance(assumptions, list)
        or any((not isinstance(x, int)) or x == 0 for x in assumptions)
    ):
        return {
            "ok": False,
            "tool": "sat_solve",
            "error": "Le champ 'assumptions' doit etre une liste d'entiers non nuls.",
        }

    names = _normalize_var_names(var_names)
    n_vars = max((abs(lit) for cl in clauses for lit in cl), default=0)
    max_models = max(1, int(max_models))

    solver = Glucose3(bootstrap_with=clauses)
    raw_models: list[list[int]] = []
    try:
        assume = list(assumptions) if assumptions else []
        while solver.solve(assumptions=assume):
            model = solver.get_model() or []
            raw_models.append(model)
            if len(raw_models) >= max_models:
                break
            block = [-lit for lit in model if abs(lit) <= n_vars]
            if not block:
                break
            solver.add_clause(block)
    finally:
        solver.delete()

    if not raw_models:
        return {
            "ok": True,
            "tool": "sat_solve",
            "status": "UNSAT",
            "n_vars": n_vars,
            "n_clauses": len(clauses),
            "models": [],
            "summary": "UNSAT — les contraintes sont contradictoires : aucune "
            "affectation ne satisfait toutes les clauses.",
        }

    models_out = []
    for model in raw_models:
        truth = {abs(lit): (lit > 0) for lit in model}
        assignment = {
            names.get(i, str(i)): bool(truth.get(i, False)) for i in range(1, n_vars + 1)
        }
        models_out.append(assignment)

    first = ", ".join(f"{k}={v}" for k, v in models_out[0].items())
    plural = f" ({len(models_out)} modeles enumeres)" if len(models_out) > 1 else ""
    return {
        "ok": True,
        "tool": "sat_solve",
        "status": "SAT",
        "n_vars": n_vars,
        "n_clauses": len(clauses),
        "models": models_out,
        "summary": f"SAT — au moins une affectation satisfait les contraintes{plural}. "
        f"Exemple : {first}.",
    }
