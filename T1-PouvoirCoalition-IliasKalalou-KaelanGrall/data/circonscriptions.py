from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

# Objectif 3, volet donnees par candidat. L'enonce evoque les 577 circonscriptions
# et les resultats par candidat publies sur data.gouv.fr. Ce module fournit la
# chaine qui va du resultat par circonscription au poids d'un acteur dans le jeu
# de vote pondere : agregation des elus par nuance politique.
#
# Limite assumee et instructive : la nuance d'un candidat (fournie par le
# ministere de l'Interieur) ne determine pas a elle seule le groupe parlementaire.
# Les groupes se constituent apres l'election ; une meme nuance "Union de la
# gauche" se repartit ensuite entre LFI, Socialistes, Ecologistes et GDR. La
# repartition finale en groupes, elle, provient de l'Assemblee nationale. C'est
# pourquoi le projet modelise les acteurs au niveau des groupes constitues (voir
# data/legislatives_2024.py), le niveau pertinent pour un indice de pouvoir : le
# jeu de vote pondere est entierement determine par la repartition des sieges
# entre acteurs votant en bloc, non par l'etiquette de campagne de chaque elu.


@dataclass(frozen=True)
class CirconscriptionResult:
    """Resultat par circonscription : departement, numero et nuance de l'elu."""

    departement: str
    circonscription: int
    nuance_elu: str


def seats_by_nuance(results: list[CirconscriptionResult]) -> dict[str, int]:
    """Nombre de sieges remportes par nuance politique, un siege par circonscription."""
    counter: Counter[str] = Counter(r.nuance_elu for r in results)
    return dict(counter)


def total_seats(results: list[CirconscriptionResult]) -> int:
    """Nombre total de sieges pourvus (une circonscription, un siege)."""
    return len(results)


def aggregate_to_groups(
    seats_nuance: dict[str, int],
    nuance_to_group: dict[str, str],
) -> dict[str, int]:
    """
    Agrege les sieges par nuance vers les groupes parlementaires selon une table de
    correspondance. Toute nuance absente de la table declenche une erreur explicite,
    pour ne jamais perdre silencieusement des sieges.
    """
    groups: dict[str, int] = {}
    for nuance, seats in seats_nuance.items():
        if nuance not in nuance_to_group:
            raise KeyError(f"Nuance sans correspondance de groupe : {nuance!r}.")
        group = nuance_to_group[nuance]
        groups[group] = groups.get(group, 0) + seats
    return groups


def load_interieur_csv(
    path: str | Path,
    departement_col: str = "Code du département",
    circonscription_col: str = "Code de la circonscription",
    nuance_col: str = "Nuance candidat",
    elu_col: str = "Elu",
    elu_true: str = "OUI",
    delimiter: str = ";",
) -> list[CirconscriptionResult]:
    """
    Charge les resultats officiels par circonscription au format data.gouv.fr /
    ministere de l'Interieur. Une ligne par candidat ; on ne retient que les elus.
    Les noms de colonnes sont parametrables car le schema varie d'un millesime a
    l'autre. Le fichier volumineux n'est pas versionne dans le depot ; cette
    fonction permet de le rejouer localement pour reconstituer les nuances.
    """
    results: list[CirconscriptionResult] = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for row in reader:
            if row.get(elu_col, "").strip().upper() != elu_true:
                continue
            results.append(
                CirconscriptionResult(
                    departement=row[departement_col].strip(),
                    circonscription=int(row[circonscription_col]),
                    nuance_elu=row[nuance_col].strip(),
                )
            )
    return results
