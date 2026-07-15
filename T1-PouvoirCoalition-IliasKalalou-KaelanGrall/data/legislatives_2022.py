from __future__ import annotations

from core.games import WeightedVotingGame
from data.legislatives_2024 import ParliamentaryGroup

ABSOLUTE_MAJORITY = 289
TOTAL_SEATS = 577

# XVIe legislature (elections de juin 2022), effectifs des groupes.
# Source : https://www.assemblee-nationale.fr/dyn/les-groupes-politiques
GROUPS_2022: tuple[ParliamentaryGroup, ...] = (
    ParliamentaryGroup("RE", "Renaissance", 172),
    ParliamentaryGroup("RN", "Rassemblement National", 89),
    ParliamentaryGroup("LFI", "La France insoumise (NUPES)", 75),
    ParliamentaryGroup("LR", "Les Republicains", 62),
    ParliamentaryGroup("DEM", "Democrate (MoDem et Independants)", 48),
    ParliamentaryGroup("SOC", "Socialistes et apparentes", 31),
    ParliamentaryGroup("HOR", "Horizons et apparentes", 30),
    ParliamentaryGroup("ECO", "Ecologiste (NUPES)", 23),
    ParliamentaryGroup("GDR", "Gauche Democrate et Republicaine (NUPES)", 22),
    ParliamentaryGroup("LIOT", "Libertes, Independants, Outre-mer et Territoires", 20),
)

NON_INSCRITS_2022 = 5


def majority_game_2022(include_non_inscrits: bool = False) -> WeightedVotingGame:
    """Jeu a la majorite absolue (quota 289) sur les groupes constitues."""
    groups = list(GROUPS_2022)
    weights = [g.seats for g in groups]
    names = [g.code for g in groups]

    if include_non_inscrits:
        weights.append(NON_INSCRITS_2022)
        names.append("NI")

    return WeightedVotingGame(
        weights=tuple(weights),
        quota=ABSOLUTE_MAJORITY,
        names=tuple(names),
    )
