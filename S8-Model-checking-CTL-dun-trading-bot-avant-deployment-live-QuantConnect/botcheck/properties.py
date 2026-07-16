from __future__ import annotations

from typing import List, Tuple

from .ctl import AF, AG, AX, EF, Atom, Formula, Implies, Not

A = Atom

def ctl_properties() -> List[Tuple[str, str, Formula]]:
    return [
        (
            "P1_no_margin_call",
            "Surete : jamais d'appel de marge (AG !margin_call)",
            AG(Not(A("margin_call"))),
        ),
        (
            "P2_leverage_bound",
            "Surete : le levier ne depasse jamais 2x (AG !leverage_breach)",
            AG(Not(A("leverage_breach"))),
        ),
        (
            "P3_no_buy_in_drawdown",
            "Surete : en zone d'alerte, le bot n'entre pas en position a "
            "l'etape suivante (AG ((dd_warn & flat) -> AX !in_position)) "
            "-- encodage fidele de 'AG (drawdown>0.15 -> AX !buy)'",
            AG(Implies(A("dd_warn") & A("flat"), AX(Not(A("in_position"))))),
        ),
        (
            "P4_halt_flattens",
            "Vivacite : apres un halt, le bot revient toujours a flat "
            "(AG (halted -> AF flat))",
            AG(Implies(A("halted"), AF(A("flat")))),
        ),
        (
            "P5_warning_flattens",
            "Vivacite : une alerte de marge conduit toujours a flat "
            "(AG (margin_warning -> AF flat))",
            AG(Implies(A("margin_warning"), AF(A("flat")))),
        ),
        (
            "P6_long_can_exit",
            "Atteignabilite : depuis toute position longue, flat est atteignable "
            "(AG (long -> EF flat))",
            AG(Implies(A("long"), EF(A("flat")))),
        ),
        (
            "P7_profit_reachable",
            "Vivacite (possibilite) : la cible de profit est atteignable "
            "(EF profit_target)",
            EF(A("profit_target")),
        ),
        (
            "P8_crit_dd_recovers",
            "Vivacite : un drawdown critique est toujours suivi d'un retour a flat "
            "(AG (dd_crit -> AF flat))",
            AG(Implies(A("dd_crit"), AF(A("flat")))),
        ),
    ]

def pctl_queries() -> List[dict]:
    return [
        {
            "id": "Q1_safety_margin",
            "desc": "Proba (pire cas) de ne JAMAIS subir de margin call "
                    "P>=0.99 [ G !margin_call ]",
            "kind": "G_not", "ap": "margin_call", "maximize": False,
            "op": ">=", "threshold": 0.99,
        },
        {
            "id": "Q2_reach_profit",
            "desc": "Proba (meilleur cas) d'atteindre la cible de profit",
            "kind": "F", "ap": "profit_target", "maximize": True,
            "op": ">=", "threshold": 0.50,
        },
        {
            "id": "Q3_reach_warning",
            "desc": "Proba (pire cas) d'entrer un jour en zone d'alerte de marge",
            "kind": "F", "ap": "dd_warn", "maximize": True,
            "op": "<=", "threshold": 1.0,
        },
    ]
