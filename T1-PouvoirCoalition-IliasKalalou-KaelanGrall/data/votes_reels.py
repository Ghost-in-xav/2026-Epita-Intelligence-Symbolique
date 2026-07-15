from __future__ import annotations

from dataclasses import dataclass, field

from data.legislatives_2024 import GROUPS_2024, majority_game_2024
from indices.shapley_shubik import shapley_shubik_exact

# Vote reel : motion de censure du 4 decembre 2024 contre le gouvernement Barnier,
# deposee par le Nouveau Front Populaire apres l'engagement de responsabilite
# (article 49 alinea 3) sur le budget de la securite sociale. Adoptee : 331 voix
# pour sur 574 votants. Le seuil requis ce jour-la etait de 288 voix, et non 289 :
# trois sieges etaient vacants, la majorite se calculant sur les membres en
# fonction. Le gouvernement est renverse pour la premiere fois depuis 1962.
# Source : Assemblee nationale, scrutin public n° 483 de la XVIIe legislature.
#
# La coalition qui a vote la censure reunit la gauche (NFP) et l'extreme droite
# (RN et UDR de Ciotti) : deux blocs ideologiquement opposes convergeant sur un
# vote negatif. C'est le cas d'ecole que l'indice de pouvoir a priori, aveugle a
# l'ideologie, ne peut pas anticiper.
#
# Detail par groupe des voix pour, verifie sur le scrutin officiel : la gauche a
# vote la motion a la quasi-unanimite, le RN presque en bloc. Deux voix pour sont
# venues de l'exterieur des six groupes deposants (un non-inscrit, un depute LIOT).

# Voix pour au sein des six groupes formant la coalition de censure.
VOTES_FOR_BY_GROUP: dict[str, int] = {
    "LFI": 71,
    "SOC": 65,
    "EcoS": 38,
    "GDR": 16,
    "RN": 123,
    "UDR": 16,
}

# Voix pour venues de deputes hors des six groupes deposants.
EXTERNAL_VOTES_FOR: dict[str, int] = {
    "NI": 1,
    "LIOT": 1,
}

# Seuil effectif du 4 decembre 2024 : majorite des membres en fonction (574),
# distincte de la majorite absolue nominale des 577 sieges (289).
CENSURE_MAJORITY_REQUIRED = 288
VOTANTS_2024_12_04 = 574


@dataclass(frozen=True)
class RollCallVote:
    """Scrutin public reel : intitule, date, groupes ayant vote pour, voix pour."""

    title: str
    date: str
    supporting_groups: tuple[str, ...]
    votes_for: int
    majority_required: int
    votes_for_by_group: dict[str, int] = field(default_factory=dict)
    external_votes_for: dict[str, int] = field(default_factory=dict)


CENSURE_BARNIER_2024 = RollCallVote(
    title="Motion de censure du gouvernement Barnier",
    date="2024-12-04",
    supporting_groups=("LFI", "SOC", "EcoS", "GDR", "RN", "UDR"),
    votes_for=331,
    majority_required=CENSURE_MAJORITY_REQUIRED,
    votes_for_by_group=VOTES_FOR_BY_GROUP,
    external_votes_for=EXTERNAL_VOTES_FOR,
)


def discipline_breakdown(vote: RollCallVote) -> dict[str, object]:
    """
    Decompose l'ecart entre les sieges des groupes deposants et les voix reelles.
    L'ecart net (sieges - voix pour) confond en realite deux mouvements opposes :
    des defections internes a la coalition et des ralliements venus de l'exterieur.
    Cette decomposition evite de lire l'ecart net comme un simple taux de defection.
    """
    seats = {g.code: g.seats for g in GROUPS_2024}

    per_group = []
    internal_seats = 0
    internal_votes = 0
    for code in vote.supporting_groups:
        group_seats = seats[code]
        group_votes = vote.votes_for_by_group.get(code, 0)
        internal_seats += group_seats
        internal_votes += group_votes
        per_group.append(
            {
                "groupe": code,
                "sieges": group_seats,
                "voix_pour": group_votes,
                "defections": group_seats - group_votes,
            }
        )

    internal_defections = internal_seats - internal_votes
    external_ralliements = sum(vote.external_votes_for.values())

    return {
        "sieges_coalition": internal_seats,
        "voix_internes": internal_votes,
        "defections_internes": internal_defections,
        "ralliements_externes": external_ralliements,
        "voix_pour_total": internal_votes + external_ralliements,
        "ecart_net_sieges_voix": internal_seats - vote.votes_for,
        "detail_par_groupe": per_group,
    }


def analyze_observed_vote(vote: RollCallVote) -> dict[str, object]:
    """
    Confronte l'objectif 4 : la coalition reellement formee lors d'un scrutin
    contre son analyse theorique. Renvoie notamment l'ecart de discipline (sieges
    des groupes soutenant la motion moins voix effectivement recueillies), les
    groupes qui etaient critiques dans la coalition observee, et la question de la
    minimalite. Le jeu est celui des groupes de 2024 (acteurs unitaires).
    """
    game = majority_game_2024()
    idx = {name: i for i, name in enumerate(game.names)}
    seats = {g.code: g.seats for g in GROUPS_2024}

    coalition = frozenset(idx[c] for c in vote.supporting_groups)
    seats_if_perfect_discipline = sum(seats[c] for c in vote.supporting_groups)
    discipline_gap = seats_if_perfect_discipline - vote.votes_for

    critical = tuple(
        game.names[i] for i in sorted(coalition) if game.is_critical(i, coalition)
    )

    breakdown = discipline_breakdown(vote)

    return {
        "titre": vote.title,
        "date": vote.date,
        "coalition_observee": vote.supporting_groups,
        "sieges_si_discipline_parfaite": seats_if_perfect_discipline,
        "voix_pour_observees": vote.votes_for,
        "majorite_requise": vote.majority_required,
        "ecart_discipline": discipline_gap,
        "defections_internes": breakdown["defections_internes"],
        "ralliements_externes": breakdown["ralliements_externes"],
        "coalition_gagnante": game.is_winning(coalition),
        "coalition_minimale": game.is_minimal_winning(coalition),
        "groupes_critiques_observes": critical,
    }


def observed_versus_theoretical(vote: RollCallVote = CENSURE_BARNIER_2024) -> dict[str, object]:
    """
    Compare le classement de pouvoir a priori (Shapley-Shubik sur l'ensemble des
    coalitions possibles) au comportement observe. L'ecart illustre la limite des
    indices a priori : ils ponderent toutes les coalitions comme equiprobables,
    alors que le vote reel selectionne une coalition ideologiquement improbable.

    La comparaison quantitative reste bornee par nature : un scrutin unique ne
    fournit pas de frequence empirique de pivot ; il fournit une seule coalition
    observee, dont on mesure la criticite effective face au rang theorique.
    """
    game = majority_game_2024()
    ss = shapley_shubik_exact(game)
    ranking = sorted(
        ((game.names[i], ss[i]) for i in game.players),
        key=lambda kv: kv[1],
        reverse=True,
    )

    observed = analyze_observed_vote(vote)
    return {
        "classement_pouvoir_a_priori": ranking,
        "coalition_reellement_formee": vote.supporting_groups,
        "ecart_discipline": observed["ecart_discipline"],
        "defections_internes": observed["defections_internes"],
        "ralliements_externes": observed["ralliements_externes"],
        "coalition_minimale": observed["coalition_minimale"],
        "groupes_critiques_observes": observed["groupes_critiques_observes"],
    }
