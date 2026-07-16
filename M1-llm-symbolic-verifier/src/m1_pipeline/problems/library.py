"""Benchmark problems.

Each entry pairs a natural-language statement (for the LLM) with a Z3 ground
truth (for the verifier). Domains span Boolean logic, logic grids, graph
colouring, scheduling, linear arithmetic and a deliberately unsatisfiable trap.
"""
from __future__ import annotations

import z3

from .base import Problem


def _domain(var: z3.ArithRef, lo: int, hi: int) -> z3.BoolRef:
    return z3.And(var >= lo, var <= hi)


# --------------------------------------------------------------------------- #
# 1. Knights & knaves (Boolean logic)
# --------------------------------------------------------------------------- #
def _knights_knaves():
    A, B, C = z3.Bools("A B C")  # True = knight (truth-teller)
    cons = [
        A == z3.Not(B),       # A says: "B is a knave"
        B == (A == C),        # B says: "A and C are the same type"
        C == B,               # C says: "B is a knight"
    ]
    return {"A": A, "B": B, "C": C}, cons


KNIGHTS_KNAVES = Problem(
    id="knights_knaves",
    title="Knights and knaves",
    domain="boolean-logic",
    statement=(
        "On an island every inhabitant is either a knight (always tells the "
        "truth) or a knave (always lies). Three inhabitants A, B and C speak:\n"
        "- A says: \"B is a knave.\"\n"
        "- B says: \"A and C are of the same type.\"\n"
        "- C says: \"B is a knight.\"\n"
        "Determine the type of each inhabitant."
    ),
    answer_format='{"A": <true if knight else false>, "B": ..., "C": ...}',
    builder=_knights_knaves,
    few_shot=(
        'Example — A says "I am a knave": this is impossible for both types, '
        "so treat each statement S by speaker X as the constraint X == S."
    ),
    tags=["logic", "sat"],
)


# --------------------------------------------------------------------------- #
# 2. Mini logic grid (zebra-style)
# --------------------------------------------------------------------------- #
def _zebra_mini():
    nor, brit, swede, dane = z3.Ints("nor brit swede dane")
    vs = {"nor": nor, "brit": brit, "swede": swede, "dane": dane}
    cons = [
        *[_domain(v, 1, 4) for v in vs.values()],
        z3.Distinct(*vs.values()),
        nor == 1,             # the Norwegian lives in house 1
        brit == swede + 1,    # the Brit lives directly right of the Swede
        dane == 4,            # the Dane lives in house 4
    ]
    return vs, cons


ZEBRA_MINI = Problem(
    id="zebra_mini",
    title="Mini logic grid",
    domain="logic-grid",
    statement=(
        "Four houses stand in a row, numbered 1 (leftmost) to 4 (rightmost). "
        "Four people of different nationalities each live in a distinct house: "
        "a Norwegian, a Brit, a Swede and a Dane. Clues:\n"
        "- The Norwegian lives in house 1.\n"
        "- The Brit lives directly to the right of the Swede.\n"
        "- The Dane lives in house 4.\n"
        "Give the house number (1-4) of each person."
    ),
    answer_format='{"nor": <1-4>, "brit": <1-4>, "swede": <1-4>, "dane": <1-4>}',
    tags=["csp", "logic-grid"],
    builder=_zebra_mini,
)


# --------------------------------------------------------------------------- #
# 3. Graph 3-colouring
# --------------------------------------------------------------------------- #
def _graph_coloring():
    A, B, C, D, E = z3.Ints("A B C D E")
    vs = {"A": A, "B": B, "C": C, "D": D, "E": E}
    edges = [(A, B), (B, C), (C, D), (D, E), (E, A), (A, C)]
    cons = [
        *[_domain(v, 1, 3) for v in vs.values()],
        *[u != w for u, w in edges],
    ]
    return vs, cons


GRAPH_COLORING = Problem(
    id="graph_coloring",
    title="Graph 3-colouring",
    domain="graph-coloring",
    statement=(
        "Colour the 5 vertices A, B, C, D, E of a graph using colours 1, 2 or 3 "
        "so that adjacent vertices get different colours. Edges: A-B, B-C, C-D, "
        "D-E, E-A and A-C. Give a colour (1, 2 or 3) for each vertex."
    ),
    answer_format='{"A": <1-3>, "B": <1-3>, "C": <1-3>, "D": <1-3>, "E": <1-3>}',
    tags=["csp", "coloring"],
    builder=_graph_coloring,
)


# --------------------------------------------------------------------------- #
# 4. Single-machine scheduling
# --------------------------------------------------------------------------- #
def _scheduling():
    t1, t2, t3 = z3.Ints("t1 t2 t3")
    vs = {"t1": t1, "t2": t2, "t3": t3}
    cons = [
        *[_domain(v, 1, 3) for v in vs.values()],
        z3.Distinct(t1, t2, t3),
        t1 < t2,        # task 1 must finish before task 2 starts
        t3 != 2,        # task 3 cannot run in slot 2
    ]
    return vs, cons


SCHEDULING = Problem(
    id="scheduling",
    title="Single-machine scheduling",
    domain="scheduling",
    statement=(
        "A machine runs exactly one task per time slot. Schedule tasks 1, 2 and "
        "3 into the three slots 1, 2 and 3 (each task in a distinct slot) such "
        "that:\n"
        "- Task 1 runs before task 2.\n"
        "- Task 3 does not run in slot 2.\n"
        "Give the slot (1-3) assigned to each task."
    ),
    answer_format='{"t1": <1-3>, "t2": <1-3>, "t3": <1-3>}',
    tags=["csp", "scheduling"],
    builder=_scheduling,
)


# --------------------------------------------------------------------------- #
# 5. Linear arithmetic system
# --------------------------------------------------------------------------- #
def _linear_arith():
    x, y, z = z3.Ints("x y z")
    vs = {"x": x, "y": y, "z": z}
    cons = [
        *[_domain(v, 0, 20) for v in vs.values()],
        x + y + z == 30,
        2 * x + 4 * y + 2 * z == 80,
        x - z == 4,
    ]
    return vs, cons


LINEAR_ARITH = Problem(
    id="linear_arith",
    title="Linear arithmetic system",
    domain="linear-arithmetic",
    statement=(
        "Find non-negative integers x, y, z (each between 0 and 20) such that:\n"
        "- x + y + z = 30\n"
        "- 2x + 4y + 2z = 80\n"
        "- x - z = 4"
    ),
    answer_format='{"x": <0-20>, "y": <0-20>, "z": <0-20>}',
    tags=["arithmetic", "smt"],
    builder=_linear_arith,
)


# --------------------------------------------------------------------------- #
# 6. 3x3 magic square
# --------------------------------------------------------------------------- #
def _magic_square():
    cells = {f"c{r}{c}": z3.Int(f"c{r}{c}") for r in range(1, 4) for c in range(1, 4)}
    g = [[cells[f"c{r}{c}"] for c in range(1, 4)] for r in range(1, 4)]
    cons = [
        *[_domain(v, 1, 9) for v in cells.values()],
        z3.Distinct(*cells.values()),
    ]
    cons += [z3.Sum(g[r]) == 15 for r in range(3)]                       # rows
    cons += [z3.Sum([g[r][c] for r in range(3)]) == 15 for c in range(3)]  # cols
    cons += [z3.Sum([g[i][i] for i in range(3)]) == 15]                  # main diag
    cons += [z3.Sum([g[i][2 - i] for i in range(3)]) == 15]             # anti diag
    return cells, cons


MAGIC_SQUARE = Problem(
    id="magic_square",
    title="3x3 magic square",
    domain="arithmetic-csp",
    statement=(
        "Fill a 3x3 grid with the digits 1 to 9, each used exactly once, so that "
        "every row, every column and both main diagonals sum to 15. Name the "
        "cells c<row><col>, e.g. c11 is top-left, c33 is bottom-right."
    ),
    answer_format=(
        '{"c11":..,"c12":..,"c13":..,"c21":..,"c22":..,"c23":..,'
        '"c31":..,"c32":..,"c33":..} each a distinct digit 1-9'
    ),
    tags=["arithmetic", "csp"],
    builder=_magic_square,
)


# --------------------------------------------------------------------------- #
# 7. Unsatisfiable trap (pigeonhole)
# --------------------------------------------------------------------------- #
def _unsat_trap():
    a, b, c = z3.Ints("a b c")
    vs = {"a": a, "b": b, "c": c}
    cons = [
        *[_domain(v, 1, 2) for v in vs.values()],
        z3.Distinct(a, b, c),  # 3 distinct values in {1,2} -> impossible
    ]
    return vs, cons


UNSAT_TRAP = Problem(
    id="unsat_trap",
    title="Pigeonhole trap (no solution)",
    domain="unsat",
    statement=(
        "Assign three pigeons a, b, c to holes numbered 1 or 2 so that no two "
        "pigeons share a hole. Give a hole (1 or 2) for each pigeon."
    ),
    answer_format='{"a": <1-2>, "b": <1-2>, "c": <1-2>}',
    satisfiable=False,
    tags=["unsat", "trap"],
    builder=_unsat_trap,
)


ALL_PROBLEMS: list[Problem] = [
    KNIGHTS_KNAVES,
    ZEBRA_MINI,
    GRAPH_COLORING,
    SCHEDULING,
    LINEAR_ARITH,
    MAGIC_SQUARE,
    UNSAT_TRAP,
]

BY_ID: dict[str, Problem] = {p.id: p for p in ALL_PROBLEMS}


def get_problem(pid: str) -> Problem:
    if pid not in BY_ID:
        raise KeyError(f"unknown problem {pid!r}; known: {list(BY_ID)}")
    return BY_ID[pid]
