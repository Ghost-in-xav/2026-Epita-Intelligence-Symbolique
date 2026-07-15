import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.legislatives_2024 import GROUPS_2024
from data.votes_reels import (
    CENSURE_BARNIER_2024,
    analyze_observed_vote,
    discipline_breakdown,
    observed_versus_theoretical,
)


def test_censure_coalition_is_winning():
    result = analyze_observed_vote(CENSURE_BARNIER_2024)
    assert result["coalition_gagnante"] is True
    # Seuil effectif du 4 decembre 2024 : 288 (trois sieges vacants), pas 289.
    assert result["majorite_requise"] == 288


def test_censure_votes_by_group_sum_to_total():
    # Les voix par groupe plus les ralliements externes reconstituent les 331 voix.
    internes = sum(CENSURE_BARNIER_2024.votes_for_by_group.values())
    externes = sum(CENSURE_BARNIER_2024.external_votes_for.values())
    assert internes == 329
    assert externes == 2
    assert internes + externes == CENSURE_BARNIER_2024.votes_for == 331


def test_censure_discipline_decomposition():
    # L'ecart net de 4 confond 6 defections internes et 2 ralliements externes.
    breakdown = discipline_breakdown(CENSURE_BARNIER_2024)
    assert breakdown["sieges_coalition"] == 335
    assert breakdown["voix_internes"] == 329
    assert breakdown["defections_internes"] == 6
    assert breakdown["ralliements_externes"] == 2
    assert breakdown["ecart_net_sieges_voix"] == 4
    assert breakdown["defections_internes"] - breakdown["ralliements_externes"] == 4


def test_censure_votes_by_group_never_exceed_group_size():
    seats = {g.code: g.seats for g in GROUPS_2024}
    for code, votes in CENSURE_BARNIER_2024.votes_for_by_group.items():
        assert 0 <= votes <= seats[code]


def test_censure_discipline_gap_is_positive():
    # Sieges des groupes soutenant la motion (335) contre voix reelles (331) :
    # l'ecart materialise l'imperfection de la discipline de parti.
    result = analyze_observed_vote(CENSURE_BARNIER_2024)
    assert result["sieges_si_discipline_parfaite"] == 335
    assert result["voix_pour_observees"] == 331
    assert result["ecart_discipline"] == 4


def test_censure_coalition_not_minimal():
    # Certains groupes soutenant la motion n'etaient pas critiques : la coalition
    # observee est gagnante mais non minimale.
    result = analyze_observed_vote(CENSURE_BARNIER_2024)
    assert result["coalition_minimale"] is False


def test_critical_groups_are_the_large_ones():
    result = analyze_observed_vote(CENSURE_BARNIER_2024)
    critical = set(result["groupes_critiques_observes"])
    assert critical == {"RN", "LFI", "SOC"}


def test_observed_versus_theoretical_exposes_ranking():
    result = observed_versus_theoretical()
    ranking = result["classement_pouvoir_a_priori"]
    assert ranking[0][0] == "RN"  # premier pouvoir a priori
    assert result["coalition_reellement_formee"] == CENSURE_BARNIER_2024.supporting_groups
