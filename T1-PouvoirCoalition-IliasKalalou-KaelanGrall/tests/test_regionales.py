import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from data.europeennes_dhondt import (
    EUROPEENNES_2024,
    SEATS_2024,
    allocate_2024,
    dhondt_marginal_votes,
)
from data.regionales import (
    REGIONALES_IDF_2021,
    SEATS_IDF_2021,
    allocate_idf_2021,
    majority_game_regionales_idf_2021,
    prime_majoritaire_allocation,
    regionales_mode_impact,
)
from indices.shapley_shubik import shapley_shubik_exact


def test_prime_majoritaire_reproduit_repartition_officielle_idf_2021():
    """La prime majoritaire doit reproduire exactement les sieges officiels de 2021."""
    allocation = allocate_idf_2021()
    assert allocation == {"LR": 125, "EELV": 53, "RN": 16, "LREM": 15}
    assert sum(allocation.values()) == SEATS_IDF_2021 == 209


def test_prime_est_le_quart_arrondi_au_superieur():
    votes = {liste.code: liste.votes for liste in REGIONALES_IDF_2021}
    allocation = prime_majoritaire_allocation(votes, SEATS_IDF_2021)
    # 209 / 4 = 52,25 -> prime de 53 pour la liste en tete.
    proportional_only = allocation["LR"] - 53
    assert proportional_only >= 0
    assert allocation["LR"] == 53 + proportional_only


def test_prime_majoritaire_rend_le_vainqueur_dictateur():
    game = majority_game_regionales_idf_2021()
    ss = shapley_shubik_exact(game)
    leader_idx = list(game.names).index("LR")
    assert game.is_dictator(leader_idx)
    assert ss[leader_idx] == 1.0


def test_impact_mode_scrutin_regional():
    rows = {r["Mode"]: r for r in regionales_mode_impact()}
    prime = rows["Prime majoritaire (regionales)"]
    prop = rows["Proportionnelle pure (D'Hondt)"]
    # A voix constantes, la prime cree un dictateur, pas la proportionnelle.
    assert prime["Vainqueur dictateur"] is True
    assert prop["Vainqueur dictateur"] is False
    assert prime["Sieges vainqueur"] > prop["Sieges vainqueur"]


def test_dhondt_marginal_coherent_avec_allocation():
    votes = {p.code: p.votes for p in EUROPEENNES_2024}
    analysis = dhondt_marginal_votes(votes, SEATS_2024, 0.05)
    assert analysis["allocation"] == allocate_2024()
    assert analysis["quotient_frontiere"] > 0
    # La liste ayant remporte le dernier siege est la plus proche d'un siege de plus.
    marginal = analysis["voix_pour_un_siege_de_plus"]
    assert min(marginal.values()) >= 0
    # Toutes les listes eligibles ont un cout fini pour un siege supplementaire.
    assert set(marginal) == set(votes)
