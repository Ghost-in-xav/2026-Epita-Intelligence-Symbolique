import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.circonscriptions import (
    CirconscriptionResult,
    aggregate_to_groups,
    load_interieur_csv,
    seats_by_nuance,
    total_seats,
)

# Jeu d'essai synthetique (et non des resultats reels) : il sert uniquement a
# valider l'arithmetique d'agregation candidat -> nuance -> groupe.
FIXTURE = [
    CirconscriptionResult("75", 1, "ENS"),
    CirconscriptionResult("75", 2, "RN"),
    CirconscriptionResult("75", 3, "UG"),
    CirconscriptionResult("93", 1, "UG"),
    CirconscriptionResult("93", 2, "RN"),
    CirconscriptionResult("59", 1, "LR"),
]


def test_seats_by_nuance_counts_winners():
    seats = seats_by_nuance(FIXTURE)
    assert seats == {"ENS": 1, "RN": 2, "UG": 2, "LR": 1}
    assert total_seats(FIXTURE) == 6


def test_aggregate_to_groups_preserves_seat_count():
    seats = seats_by_nuance(FIXTURE)
    mapping = {"ENS": "EPR", "RN": "RN", "UG": "NFP", "LR": "DR"}
    groups = aggregate_to_groups(seats, mapping)
    assert groups == {"EPR": 1, "RN": 2, "NFP": 2, "DR": 1}
    assert sum(groups.values()) == total_seats(FIXTURE)


def test_aggregate_to_groups_rejects_unknown_nuance():
    seats = seats_by_nuance(FIXTURE)
    incomplete_mapping = {"ENS": "EPR", "RN": "RN", "UG": "NFP"}
    with pytest.raises(KeyError):
        aggregate_to_groups(seats, incomplete_mapping)


def test_load_interieur_csv_keeps_only_elected(tmp_path):
    csv_content = (
        "Code du département;Code de la circonscription;Nuance candidat;Elu\n"
        "75;1;ENS;OUI\n"
        "75;1;RN;NON\n"
        "75;2;RN;OUI\n"
        "93;1;UG;OUI\n"
    )
    csv_file = tmp_path / "resultats.csv"
    csv_file.write_text(csv_content, encoding="utf-8")

    results = load_interieur_csv(csv_file)
    assert total_seats(results) == 3
    assert seats_by_nuance(results) == {"ENS": 1, "RN": 1, "UG": 1}
