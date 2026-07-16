"""Couche 3 — Raisonnement qualitatif sur les transitions de régime.

Objectif S4 #3 : contraindre les transitions à être logiquement cohérentes.
On refuse les sauts absurdes (ex : bull -> bear direct sans passer par range).

On modélise une petite **algèbre de transition** : un graphe des transitions
autorisées. Une transition interdite proposée par la couche précédente est
corrigée en insérant le régime pont (range), qui est le seul état par lequel on
peut passer entre bull et bear.

Inspiration : probabilité qualitative / réseaux probabilistes qualitatifs
(Wellman 1990) — on raisonne sur la *structure* admissible des transitions
plutôt que sur des nombres.
"""
from __future__ import annotations

import pandas as pd

REGIMES = ["bear", "range", "bull"]

ALLOWED = {
    "bear":  {"bear", "range"},
    "range": {"bear", "range", "bull"},
    "bull":  {"range", "bull"},
}
BRIDGE = "range"


def enforce_transitions(regimes: pd.Series, allowed: dict = ALLOWED) -> pd.Series:
    """Corrige les transitions interdites en insérant le régime pont.

    Parcourt la série ; si passer de `prev` à `cur` n'est pas autorisé, on
    remplace `cur` par le régime pont (range) — transition rendue cohérente.
    """
    out = []
    prev = regimes.iloc[0]
    out.append(prev)
    for cur in regimes.iloc[1:]:
        if cur in allowed[prev]:
            out.append(cur)
            prev = cur
        else:
            out.append(BRIDGE)
            prev = BRIDGE
    return pd.Series(out, index=regimes.index, name="qualitative")


def count_illegal(regimes: pd.Series, allowed: dict = ALLOWED) -> int:
    """Compte les transitions interdites dans une série (diagnostic)."""
    n = 0
    prev = regimes.iloc[0]
    for cur in regimes.iloc[1:]:
        if cur not in allowed[prev]:
            n += 1
        prev = cur
    return n
