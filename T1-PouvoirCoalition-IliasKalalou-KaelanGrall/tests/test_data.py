import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.europeennes_dhondt import (
    SEATS_2024,
    allocate_2024,
    dhondt_allocation,
    majority_game_europeennes_2024,
)
from data.legislatives_2022 import GROUPS_2022, NON_INSCRITS_2022, majority_game_2022
from data.legislatives_2024 import (
    ABSOLUTE_MAJORITY,
    GROUPS_2024,
    NON_INSCRITS_2024,
    TOTAL_SEATS,
    majority_game_2024,
)


def test_assembly_2024_total_seats():
    total = sum(g.seats for g in GROUPS_2024) + NON_INSCRITS_2024
    assert total == TOTAL_SEATS


def test_assembly_2022_total_seats():
    total = sum(g.seats for g in GROUPS_2022) + NON_INSCRITS_2022
    assert total == 577


def test_no_majority_bloc_2024():
    assert all(g.seats < ABSOLUTE_MAJORITY for g in GROUPS_2024)


def test_majority_game_2024_quota():
    game = majority_game_2024()
    assert game.quota == ABSOLUTE_MAJORITY
    assert game.n_players == len(GROUPS_2024)


def test_majority_game_2022_quota():
    game = majority_game_2022()
    assert game.quota == 289


def test_dhondt_reproduces_official_2024():
    expected = {"RN": 30, "RE": 13, "PS": 13, "LFI": 9, "LR": 6, "ECO": 5, "REC": 5}
    allocation = allocate_2024()
    assert allocation == expected
    assert sum(allocation.values()) == SEATS_2024


def test_dhondt_conserves_total_seats():
    votes = {"A": 100_000, "B": 80_000, "C": 30_000, "D": 5_000}
    allocation = dhondt_allocation(votes, seats=10, threshold=0.0)
    assert sum(allocation.values()) == 10


def test_dhondt_threshold_excludes_small_parties():
    votes = {"A": 100_000, "B": 80_000, "C": 3_000}
    allocation = dhondt_allocation(votes, seats=10, threshold=0.05)
    assert allocation["C"] == 0
    assert sum(allocation.values()) == 10


def test_dhondt_all_parties_below_threshold():
    votes = {"A": 1_000, "B": 1_000, "C": 1_000, "D": 1_000}
    allocation = dhondt_allocation(votes, seats=5, threshold=0.50)
    assert sum(allocation.values()) == 0
    assert all(v == 0 for v in allocation.values())


def test_europeennes_game_is_valid():
    game = majority_game_europeennes_2024()
    assert game.total_weight == SEATS_2024
    assert game.quota == SEATS_2024 // 2 + 1
