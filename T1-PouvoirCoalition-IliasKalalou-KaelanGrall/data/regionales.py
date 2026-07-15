from __future__ import annotations

import math
from dataclasses import dataclass

from core.games import WeightedVotingGame, majority_game
from data.europeennes_dhondt import dhondt_allocation
from indices.shapley_shubik import shapley_shubik_exact


@dataclass(frozen=True)
class ListVotes:
    """Liste regionale : sigle, libelle et suffrages exprimes au second tour."""

    code: str
    label: str
    votes: int


# Regionales des 20 et 27 juin 2021, Ile-de-France, second tour (209 sieges).
# Source : ministere de l'Interieur et Assemblee des resultats officiels.
# Suffrages exprimes au second tour : 2 344 970.
REGIONALES_IDF_2021: tuple[ListVotes, ...] = (
    ListVotes("LR", "Pecresse (LR-UDI-Agir-MoDem-LC)", 1_076_821),
    ListVotes("EELV", "Bayou (union de la gauche et ecologistes)", 789_666),
    ListVotes("RN", "Bardella (Rassemblement National)", 253_001),
    ListVotes("LREM", "Saint-Martin (majorite presidentielle)", 225_482),
)

SEATS_IDF_2021 = 209
THRESHOLD_SECOND_ROUND = 0.05


def prime_majoritaire_allocation(
    votes: dict[str, int],
    seats: int,
    threshold: float = THRESHOLD_SECOND_ROUND,
) -> dict[str, int]:
    """
    Repartition des sieges d'un conseil regional (article L338 du code electoral).

    La liste arrivee en tete recoit d'abord une prime majoritaire egale au quart
    des sieges a pourvoir, arrondi a l'entier superieur. Les sieges restants sont
    repartis a la plus forte moyenne (methode D'Hondt) entre toutes les listes
    ayant obtenu au moins 5 % des suffrages exprimes, la liste en tete comprise.
    C'est ce mecanisme qui cree les seuils strategiques propres au scrutin
    regional : la prime concentre le pouvoir sur le vainqueur bien au-dela de sa
    part de voix.
    """
    total_votes = sum(votes.values())
    eligible = {code: v for code, v in votes.items() if v >= threshold * total_votes}

    allocation = {code: 0 for code in votes}
    if not eligible:
        return allocation

    winner = max(eligible, key=lambda code: eligible[code])
    bonus = math.ceil(seats / 4)
    allocation[winner] += bonus

    remaining = seats - bonus
    proportional = dhondt_allocation(eligible, remaining)
    for code, extra in proportional.items():
        allocation[code] += extra

    return allocation


def allocate_idf_2021() -> dict[str, int]:
    """Repartition des 209 sieges du conseil regional d'Ile-de-France en 2021."""
    votes = {liste.code: liste.votes for liste in REGIONALES_IDF_2021}
    return prime_majoritaire_allocation(votes, SEATS_IDF_2021)


def majority_game_regionales_idf_2021() -> WeightedVotingGame:
    """
    Jeu de vote a la majorite absolue (105 sur 209) sur les listes siegeant au
    conseil regional d'Ile-de-France, poids = sieges obtenus.
    """
    allocation = allocate_idf_2021()
    listes = [liste for liste in REGIONALES_IDF_2021 if allocation[liste.code] > 0]
    weights = tuple(allocation[liste.code] for liste in listes)
    names = tuple(liste.code for liste in listes)
    return majority_game(weights, names)


def _leader_power(allocation: dict[str, int]) -> tuple[str, float, float]:
    """Liste en tete, sa part de sieges et son pouvoir de pivot (Shapley-Shubik)."""
    seating = {code: s for code, s in allocation.items() if s > 0}
    total_seats = sum(seating.values())
    leader = max(seating, key=lambda code: seating[code])

    weights = tuple(seating.values())
    names = tuple(seating.keys())
    game = majority_game(weights, names)
    ss = shapley_shubik_exact(game)
    leader_idx = names.index(leader)

    return leader, seating[leader] / total_seats, ss[leader_idx]


def regionales_mode_impact() -> list[dict[str, object]]:
    """
    Objectif 5, volet regional : a suffrages constants (Ile-de-France 2021), on
    compare la prime majoritaire reelle a une proportionnelle pure D'Hondt sur les
    memes 209 sieges. La prime transforme une pluralite (45,9 % des voix) en
    majorite absolue des sieges, donc en dictateur au sens des indices de pouvoir,
    la ou la proportionnelle pure ne donnerait au vainqueur qu'un pouvoir partage.
    """
    votes = {liste.code: liste.votes for liste in REGIONALES_IDF_2021}

    prime = prime_majoritaire_allocation(votes, SEATS_IDF_2021)
    proportionnelle = dhondt_allocation(votes, SEATS_IDF_2021, THRESHOLD_SECOND_ROUND)

    rows: list[dict[str, object]] = []
    for mode, allocation in (
        ("Prime majoritaire (regionales)", prime),
        ("Proportionnelle pure (D'Hondt)", proportionnelle),
    ):
        leader, seat_share, power = _leader_power(allocation)
        rows.append(
            {
                "Mode": mode,
                "Sieges vainqueur": allocation[leader],
                "Part sieges vainqueur %": round(seat_share * 100, 1),
                "Pouvoir vainqueur (Shapley) %": round(power * 100, 1),
                "Vainqueur dictateur": power > 0.999,
            }
        )
    return rows
