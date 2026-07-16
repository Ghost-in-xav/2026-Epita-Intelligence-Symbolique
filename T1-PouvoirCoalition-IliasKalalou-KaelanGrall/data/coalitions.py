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


def _merge_groups(
    groups: tuple[ParliamentaryGroup, ...],
    merges: dict[str, tuple[str, ...]],
    quota: int = ABSOLUTE_MAJORITY,
) -> WeightedVotingGame:
    """
    Fusionne les seuls groupes cites dans merges et laisse tous les autres joueurs
    inchanges. Contrairement a aggregate_into_blocs, qui recompose toute
    l'Assemblee, cette fonction ne fait varier qu'un facteur : elle sert aux
    contrefactuels toutes choses egales par ailleurs.
    """
    seats_by_code = {g.code: g.seats for g in groups}
    cited = [code for members in merges.values() for code in members]
    unknown = set(cited) - set(seats_by_code)
    if unknown:
        raise ValueError(f"Groupes inconnus : {sorted(unknown)}.")
    if len(cited) != len(set(cited)):
        raise ValueError("Un groupe ne peut appartenir qu'a une seule fusion.")

    names: list[str] = []
    weights: list[int] = []
    for bloc_name, members in merges.items():
        names.append(bloc_name)
        weights.append(sum(seats_by_code.pop(m) for m in members))
    for code, seats in seats_by_code.items():
        names.append(code)
        weights.append(seats)
    return WeightedVotingGame(weights=tuple(weights), quota=quota, names=tuple(names))


def _year_config(year: int):
    """Groupes, gauche, nom du bloc de gauche et camp presidentiel pour une annee."""
    if year == 2022:
        return GROUPS_2022, LEFT_GROUPS_2022, "NUPES", BLOCS_2022["Ensemble"]
    if year == 2024:
        return GROUPS_2024, LEFT_GROUPS_2024, "NFP", BLOCS_2024["Ensemble"]
    raise ValueError("Annee attendue : 2022 ou 2024.")


def left_union_counterfactual(year: int) -> dict[str, float]:
    """
    Contrefactuel de l'objectif 3 : que gagne la gauche en s'unissant ?

    Toutes choses egales par ailleurs : seuls les groupes de gauche fusionnent,
    tous les autres restent des joueurs distincts. Comparer au jeu a blocs complets
    confondrait deux effets, l'union de la gauche et la consolidation simultanee du
    camp presidentiel ; union_decomposition les isole.
    """
    groups, left, bloc_name, _ = _year_config(year)

    fragmented = _shapley_by_name(_group_game(groups))
    power_fragmented = sum(fragmented[code] for code in left)

    united = _shapley_by_name(_merge_groups(groups, {bloc_name: left}))
    power_united = united[bloc_name]

    seats_by_code = {g.code: g.seats for g in groups}
    seat_share_left = sum(seats_by_code[c] for c in left) / sum(seats_by_code.values())

    return {
        "part_sieges_gauche": seat_share_left,
        "pouvoir_fragmente": power_fragmented,
        "pouvoir_uni": power_united,
        "gain_union": power_united - power_fragmented,
    }


def union_decomposition(year: int) -> dict[str, float]:
    """
    Isole les deux fusions au lieu de les confondre, en partant toujours du meme
    jeu de reference a groupes separes.

    Le pouvoir de pivot est relatif : la gauche peut en perdre sans rien faire, il
    suffit que le camp presidentiel se consolide. Comparer directement le jeu a
    groupes au jeu a blocs attribuerait a tort cette perte a l'union de la gauche.
    """
    groups, left, bloc_name, rival = _year_config(year)

    base = _shapley_by_name(_group_game(groups))
    power_base = sum(base[code] for code in left)

    only_left = _shapley_by_name(_merge_groups(groups, {bloc_name: left}))
    power_only_left = only_left[bloc_name]

    only_rival = _shapley_by_name(_merge_groups(groups, {"Ensemble": rival}))
    power_only_rival = sum(only_rival[code] for code in left)

    both = _shapley_by_name(_merge_groups(groups, {bloc_name: left, "Ensemble": rival}))
    power_both = both[bloc_name]

    return {
        "pouvoir_reference": power_base,
        "gauche_unie_seule": power_only_left,
        "effet_union_gauche": power_only_left - power_base,
        "camp_adverse_uni_seul": power_only_rival,
        "effet_consolidation_adverse": power_only_rival - power_base,
        "les_deux_unis": power_both,
        "effet_cumule": power_both - power_base,
    }
