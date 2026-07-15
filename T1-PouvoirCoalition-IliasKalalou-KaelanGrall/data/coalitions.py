from __future__ import annotations

from core.games import WeightedVotingGame
from data.legislatives_2022 import GROUPS_2022
from data.legislatives_2024 import (
    ABSOLUTE_MAJORITY,
    GROUPS_2024,
    ParliamentaryGroup,
)
from indices.shapley_shubik import shapley_shubik_exact

# Blocs politiques : partition des groupes parlementaires en alliances electorales
# reelles. Chaque bloc regroupe les groupes qui se sont federes pour la campagne
# et les scrutins de bloc. La somme des sieges d'un bloc egale la somme des sieges
# de ses groupes membres, donc la couverture des 577 sieges est conservee.
#
# 2022 (XVIe legislature) :
#   NUPES     = LFI + Ecologiste + GDR + Socialistes (union de la gauche)
#   Ensemble  = Renaissance + MoDem + Horizons (coalition presidentielle)
#   RN, LR, LIOT restent isoles.
BLOCS_2022: dict[str, tuple[str, ...]] = {
    "NUPES": ("LFI", "ECO", "GDR", "SOC"),
    "Ensemble": ("RE", "DEM", "HOR"),
    "RN": ("RN",),
    "LR": ("LR",),
    "LIOT": ("LIOT",),
}

# 2024 (XVIIe legislature) :
#   NFP       = LFI + Socialistes + Ecologiste et social + GDR (Nouveau Front Populaire)
#   Ensemble  = EPR + Les Democrates + Horizons (socle commun presidentiel)
#   RN, DR (Droite Republicaine), LIOT, UDR (allie du RN) restent isoles.
BLOCS_2024: dict[str, tuple[str, ...]] = {
    "NFP": ("LFI", "SOC", "EcoS", "GDR"),
    "Ensemble": ("EPR", "DEM", "HOR"),
    "RN": ("RN",),
    "DR": ("DR",),
    "LIOT": ("LIOT",),
    "UDR": ("UDR",),
}

# Groupes de gauche, utilises pour le contrefactuel d'union.
LEFT_GROUPS_2022 = BLOCS_2022["NUPES"]
LEFT_GROUPS_2024 = BLOCS_2024["NFP"]


def aggregate_into_blocs(
    groups: tuple[ParliamentaryGroup, ...],
    blocs: dict[str, tuple[str, ...]],
    quota: int = ABSOLUTE_MAJORITY,
) -> WeightedVotingGame:
    """
    Agrege les groupes parlementaires en blocs politiques et construit le jeu de
    vote pondere correspondant. Le poids d'un bloc est la somme des sieges de ses
    groupes membres ; chaque bloc devient un joueur unique.
    """
    seats_by_code = {g.code: g.seats for g in groups}
    known = set(seats_by_code)
    assigned = {code for members in blocs.values() for code in members}
    missing = known - assigned
    if missing:
        raise ValueError(f"Groupes non affectes a un bloc : {sorted(missing)}.")

    weights = tuple(sum(seats_by_code[m] for m in members) for members in blocs.values())
    names = tuple(blocs)
    return WeightedVotingGame(weights=weights, quota=quota, names=names)


def bloc_game_2022() -> WeightedVotingGame:
    """Jeu de vote au niveau des blocs pour la XVIe legislature (quota 289)."""
    return aggregate_into_blocs(GROUPS_2022, BLOCS_2022)


def bloc_game_2024() -> WeightedVotingGame:
    """Jeu de vote au niveau des blocs pour la XVIIe legislature (quota 289)."""
    return aggregate_into_blocs(GROUPS_2024, BLOCS_2024)


def _group_game(
    groups: tuple[ParliamentaryGroup, ...],
    quota: int = ABSOLUTE_MAJORITY,
) -> WeightedVotingGame:
    weights = tuple(g.seats for g in groups)
    names = tuple(g.code for g in groups)
    return WeightedVotingGame(weights=weights, quota=quota, names=names)


def _shapley_by_name(game: WeightedVotingGame) -> dict[str, float]:
    power = shapley_shubik_exact(game)
    return {game.names[i]: power[i] for i in game.players}


def left_union_counterfactual(year: int) -> dict[str, float]:
    """
    Contrefactuel de l'objectif 3 : quel pouvoir de pivot la gauche detient-elle
    quand elle reste fragmentee en plusieurs groupes, contre quand elle s'unit en
    un seul bloc ?

    On compare la somme des indices de Shapley-Shubik des groupes de gauche pris
    separement (dans le jeu a 10 ou 11 groupes) au Shapley-Shubik du bloc uni
    (dans le jeu a blocs). Un gain positif signifie que l'union concentre le
    pouvoir au-dela de la simple addition des sieges ; un gain negatif signifie
    que la fragmentation preservait davantage de positions de pivot.
    """
    if year == 2022:
        groups, blocs, left, bloc_name = GROUPS_2022, BLOCS_2022, LEFT_GROUPS_2022, "NUPES"
    elif year == 2024:
        groups, blocs, left, bloc_name = GROUPS_2024, BLOCS_2024, LEFT_GROUPS_2024, "NFP"
    else:
        raise ValueError("Annee attendue : 2022 ou 2024.")

    fragmented = _shapley_by_name(_group_game(groups))
    power_fragmented = sum(fragmented[code] for code in left)

    united = _shapley_by_name(aggregate_into_blocs(groups, blocs))
    power_united = united[bloc_name]

    seats_by_code = {g.code: g.seats for g in groups}
    seat_share_left = sum(seats_by_code[c] for c in left) / sum(seats_by_code.values())

    return {
        "part_sieges_gauche": seat_share_left,
        "pouvoir_fragmente": power_fragmented,
        "pouvoir_uni": power_united,
        "gain_union": power_united - power_fragmented,
    }
