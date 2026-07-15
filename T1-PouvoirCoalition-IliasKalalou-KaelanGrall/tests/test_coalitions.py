import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.coalitions import (
    BLOCS_2022,
    BLOCS_2024,
    aggregate_into_blocs,
    bloc_game_2022,
    bloc_game_2024,
    left_union_counterfactual,
)
from data.legislatives_2022 import GROUPS_2022, NON_INSCRITS_2022
from data.legislatives_2024 import ABSOLUTE_MAJORITY, GROUPS_2024, NON_INSCRITS_2024


def test_blocs_partition_all_groups_2024():
    assigned = {code for members in BLOCS_2024.values() for code in members}
    known = {g.code for g in GROUPS_2024}
    assert assigned == known


def test_blocs_partition_all_groups_2022():
    assigned = {code for members in BLOCS_2022.values() for code in members}
    known = {g.code for g in GROUPS_2022}
    assert assigned == known


def test_bloc_game_conserves_seats_2024():
    game = bloc_game_2024()
    assert game.total_weight + NON_INSCRITS_2024 == 577
    assert game.quota == ABSOLUTE_MAJORITY


def test_bloc_game_conserves_seats_2022():
    game = bloc_game_2022()
    assert game.total_weight + NON_INSCRITS_2022 == 577
    assert game.quota == ABSOLUTE_MAJORITY


def test_bloc_seats_match_component_sum_2024():
    seats = {g.code: g.seats for g in GROUPS_2024}
    game = bloc_game_2024()
    weights = dict(zip(game.names, game.weights))
    assert weights["NFP"] == seats["LFI"] + seats["SOC"] + seats["EcoS"] + seats["GDR"]
    assert weights["Ensemble"] == seats["EPR"] + seats["DEM"] + seats["HOR"]


def test_aggregate_rejects_unassigned_group():
    incomplete = {"A": ("RN",)}
    with pytest.raises(ValueError):
        aggregate_into_blocs(GROUPS_2024, incomplete)


def test_left_union_counterfactual_shape():
    result = left_union_counterfactual(2024)
    assert set(result) == {
        "part_sieges_gauche",
        "pouvoir_fragmente",
        "pouvoir_uni",
        "gain_union",
    }
    assert result["gain_union"] == pytest.approx(
        result["pouvoir_uni"] - result["pouvoir_fragmente"], abs=1e-12
    )


def test_left_union_2022_reduces_pivot_power():
    # Resultat contre-intuitif verifie : en 2022, face a une coalition
    # presidentielle proche de la majorite, unir la gauche en un seul bloc
    # detruit des positions de pivot (gain negatif).
    result = left_union_counterfactual(2022)
    assert result["gain_union"] < 0


def test_left_union_counterfactual_rejects_bad_year():
    with pytest.raises(ValueError):
        left_union_counterfactual(2020)
