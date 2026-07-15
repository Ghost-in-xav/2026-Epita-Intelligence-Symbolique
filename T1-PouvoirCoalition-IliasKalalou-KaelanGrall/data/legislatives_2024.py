from __future__ import annotations

from dataclasses import dataclass

from core.games import WeightedVotingGame


@dataclass(frozen=True)
class ParliamentaryGroup:
    """Groupe parlementaire : sigle, libelle et sieges."""

    code: str
    label: str
    seats: int


# XVIIe legislature (elections de juin-juillet 2024), effectifs des groupes tels
# que stabilises a l'automne 2024. Les effectifs des tout premiers jours de la
# legislature different legerement (par ex. LIOT et non-inscrits), mais la somme
# groupes + non-inscrits reste egale aux 577 sieges.
# Source : https://www.assemblee-nationale.fr/dyn/les-groupes-politiques
GROUPS_2024: tuple[ParliamentaryGroup, ...] = (
    ParliamentaryGroup("RN", "Rassemblement National", 126),
    ParliamentaryGroup("EPR", "Ensemble pour la Republique", 99),
    ParliamentaryGroup("LFI", "La France insoumise", 72),
    ParliamentaryGroup("SOC", "Socialistes et apparentes", 66),
    ParliamentaryGroup("DR", "Droite Republicaine", 47),
    ParliamentaryGroup("EcoS", "Ecologiste et social", 38),
    ParliamentaryGroup("DEM", "Les Democrates", 36),
    ParliamentaryGroup("HOR", "Horizons et apparentes", 31),
    ParliamentaryGroup("LIOT", "Libertes, Independants, Outre-mer et Territoires", 23),
    ParliamentaryGroup("GDR", "Gauche Democrate et Republicaine", 17),
    ParliamentaryGroup("UDR", "Union des droites pour la Republique", 16),
)

NON_INSCRITS_2024 = 6
TOTAL_SEATS = 577
ABSOLUTE_MAJORITY = 289


def majority_game_2024(include_non_inscrits: bool = False) -> WeightedVotingGame:
    """
    Jeu a la majorite absolue (quota 289) sur les groupes constitues. Les
    non-inscrits, heterogenes, ne sont agreges que sur option.
    """
    groups = list(GROUPS_2024)
    weights = [g.seats for g in groups]
    names = [g.code for g in groups]

    if include_non_inscrits:
        weights.append(NON_INSCRITS_2024)
        names.append("NI")

    return WeightedVotingGame(
        weights=tuple(weights),
        quota=ABSOLUTE_MAJORITY,
        names=tuple(names),
    )
