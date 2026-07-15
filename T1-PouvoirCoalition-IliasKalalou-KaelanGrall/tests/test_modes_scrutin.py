import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.europeennes_dhondt import EUROPEENNES_2024, SEATS_2024, allocate_2024
from data.modes_scrutin import (
    compare_scrutin_modes_2024,
    highest_averages_allocation,
    sainte_lague_allocation,
    winner_take_all_allocation,
)


def _votes() -> dict[str, int]:
    return {p.code: p.votes for p in EUROPEENNES_2024}


def test_highest_averages_reproduces_dhondt():
    # D'Hondt est la plus forte moyenne de diviseur s + 1.
    votes = _votes()
    generic = highest_averages_allocation(votes, SEATS_2024, lambda s: s + 1)
    assert generic == allocate_2024()


def test_sainte_lague_conserves_seats():
    allocation = sainte_lague_allocation(_votes(), SEATS_2024)
    assert sum(allocation.values()) == SEATS_2024


def test_sainte_lague_differs_from_dhondt():
    # Sainte-Lague favorise les petites listes : la repartition n'est pas identique.
    assert sainte_lague_allocation(_votes(), SEATS_2024) != allocate_2024()


def test_winner_take_all_gives_everything_to_leader():
    allocation = winner_take_all_allocation(_votes(), SEATS_2024)
    assert allocation["RN"] == SEATS_2024
    assert sum(allocation.values()) == SEATS_2024
    assert sum(1 for s in allocation.values() if s > 0) == 1


def test_compare_modes_returns_three_rows():
    rows = compare_scrutin_modes_2024()
    assert len(rows) == 3
    modes = {row["Mode"] for row in rows}
    assert "Majoritaire integral" in modes


def test_winner_take_all_makes_leader_a_dictator():
    # Sous scrutin majoritaire integral, le pouvoir de pivot du leader vaut 100 %.
    rows = compare_scrutin_modes_2024()
    maj = next(r for r in rows if r["Mode"] == "Majoritaire integral")
    assert maj["Pouvoir RN (Shapley) %"] == 100.0
