from __future__ import annotations

import pandas as pd
import streamlit as st

from analysis import (
    comparison_table,
    cross_validate_smt,
    montecarlo_benchmark,
    player_status_table,
)
from core.games import WeightedVotingGame
from data.europeennes_dhondt import (
    EUROPEENNES_2024,
    SEATS_2024,
    allocate_2024,
    dhondt_marginal_votes,
    majority_game_europeennes_2024,
)
from data.coalitions import (
    bloc_game_2022,
    bloc_game_2024,
    left_union_counterfactual,
    union_decomposition,
)
from data.legislatives_2022 import majority_game_2022
from data.legislatives_2024 import majority_game_2024
from data.modes_scrutin import compare_scrutin_modes_2024
from data.regionales import (
    allocate_idf_2021,
    majority_game_regionales_idf_2021,
    regionales_mode_impact,
)
from data.votes_reels import CENSURE_BARNIER_2024, analyze_observed_vote, discipline_breakdown
from formal.axioms import prove_all_axioms, prove_all_deegan_packel_axioms
from formal.distinctions import axiom_matrix
from indices.banzhaf import banzhaf_normalized, swing_counts
from indices.deegan_packel import deegan_packel
from indices.shapley_shubik import shapley_shubik_exact
from viz.coalitions import plot_critical_frequency, plot_minimal_winning_matrix
from viz.dhondt import plot_dhondt_quotients, plot_seats_bar
from viz.power_vs_weight import plot_power_gap, plot_power_vs_weight


st.set_page_config(page_title="Pouvoir de coalition", layout="wide")
st.title("Pouvoir de coalition et verification formelle")
st.caption(
    "Projet T1 - Intelligence Symbolique - Ilias Kalalou et Kaelan Grall - EPITA SCIA 2026"
)


PREDEFINED = {
    "[3 ; 2, 1, 1] - joueur dominant": WeightedVotingGame((2, 1, 1), 3),
    "[51 ; 49, 48, 3] - paradoxe du petit parti": WeightedVotingGame(
        (49, 48, 3), 51, ("A", "B", "C")
    ),
    "[4 ; 2, 2, 1] - joueur nul": WeightedVotingGame((2, 2, 1), 4),
    "Conseil de securite ONU [39 ; 5x7, 10x1]": WeightedVotingGame(
        (7,) * 5 + (1,) * 10, 39
    ),
}


def render_game_analysis(game: WeightedVotingGame) -> None:
    """Affiche indices, statuts et visualisations pour un jeu donne."""
    ss = shapley_shubik_exact(game)
    bz = banzhaf_normalized(game)
    dp = deegan_packel(game)
    swings = swing_counts(game)

    st.subheader("Indices de pouvoir")
    st.dataframe(comparison_table(game), use_container_width=True, hide_index=True)

    st.subheader("Statut des joueurs")
    st.dataframe(player_status_table(game), use_container_width=True, hide_index=True)

    st.subheader("Pouvoir contre part de sieges")
    st.pyplot(plot_power_vs_weight(game, ss, bz, dp))

    col1, col2 = st.columns(2)
    with col1:
        st.pyplot(plot_power_gap(game, ss, "Shapley-Shubik"))
    with col2:
        st.pyplot(plot_critical_frequency(game, swings))

    st.subheader("Coalitions gagnantes minimales")
    st.pyplot(plot_minimal_winning_matrix(game))


mode = st.sidebar.radio(
    "Mode",
    [
        "Analyse d'un jeu",
        "Assemblee nationale",
        "Europeennes (D'Hondt)",
        "Regionales (prime majoritaire)",
        "Verification formelle",
        "Validation symbolique",
    ],
)


if mode == "Analyse d'un jeu":
    source = st.radio("Source du jeu", ["Instance predefinie", "Saisie manuelle"], horizontal=True)

    if source == "Instance predefinie":
        choice = st.selectbox("Instance", list(PREDEFINED))
        game = PREDEFINED[choice]
    else:
        raw_weights = st.text_input("Poids (separes par des virgules)", "10, 8, 6, 4, 2")
        try:
            weights = tuple(int(w.strip()) for w in raw_weights.split(",") if w.strip())
        except ValueError:
            st.error("Les poids doivent etre des entiers.")
            st.stop()
        if not weights:
            st.warning("Saisir au moins un poids.")
            st.stop()
        default_quota = sum(weights) // 2 + 1
        quota = st.number_input(
            "Quota", min_value=1, max_value=sum(weights), value=default_quota
        )
        try:
            game = WeightedVotingGame(weights=weights, quota=int(quota))
        except ValueError as exc:
            st.error(str(exc))
            st.stop()

    st.info(f"Jeu analyse : {game}  -  propre : {game.is_proper()}")
    if game.n_players > 18:
        st.warning("Au-dela de 18 joueurs, le calcul exact peut etre lent.")
    render_game_analysis(game)


elif mode == "Assemblee nationale":
    year = st.radio("Legislature", ["2024 (XVIIe)", "2022 (XVIe)"], horizontal=True)
    with_ni = st.checkbox("Agreger les non-inscrits en un acteur (analyse de sensibilite)")
    is_2024 = year.startswith("2024")
    game = majority_game_2024(with_ni) if is_2024 else majority_game_2022(with_ni)
    st.info(
        f"Majorite absolue : {game.quota} sieges. Aucun groupe ne l'atteint seul : "
        "le pouvoir se joue dans les coalitions."
    )
    render_game_analysis(game)

    st.divider()
    st.subheader("Analyse en blocs politiques")
    st.write(
        "Le sujet demande de modeliser les coalitions reelles (NUPES/NFP, Ensemble, "
        "RN, DR), et pas seulement les groupes isoles. On agrege les groupes en blocs."
    )
    blocs = bloc_game_2024() if is_2024 else bloc_game_2022()
    st.dataframe(comparison_table(blocs), use_container_width=True, hide_index=True)

    year = 2024 if is_2024 else 2022
    cf = left_union_counterfactual(year)
    st.write(
        f"Contrefactuel d'union de la gauche, toutes choses egales par ailleurs "
        f"(seuls les groupes de gauche fusionnent) : pouvoir de pivot "
        f"{cf['pouvoir_fragmente'] * 100:.1f} % fragmentee contre "
        f"{cf['pouvoir_uni'] * 100:.1f} % unie, soit {cf['gain_union'] * 100:+.1f} points."
    )

    dec = union_decomposition(year)
    st.write(
        "Decomposition des deux effets, mesures depuis le meme jeu de reference. "
        "Le pouvoir de pivot est relatif : la gauche peut en perdre sans bouger."
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Scenario": "Reference : tous les groupes separes",
                    "Pouvoir de la gauche": f"{dec['pouvoir_reference'] * 100:.1f} %",
                    "Ecart": "-",
                },
                {
                    "Scenario": "La gauche seule s'unit",
                    "Pouvoir de la gauche": f"{dec['gauche_unie_seule'] * 100:.1f} %",
                    "Ecart": f"{dec['effet_union_gauche'] * 100:+.1f} pt",
                },
                {
                    "Scenario": "Le camp presidentiel seul se consolide",
                    "Pouvoir de la gauche": f"{dec['camp_adverse_uni_seul'] * 100:.1f} %",
                    "Ecart": f"{dec['effet_consolidation_adverse'] * 100:+.1f} pt",
                },
                {
                    "Scenario": "Les deux a la fois",
                    "Pouvoir de la gauche": f"{dec['les_deux_unis'] * 100:.1f} %",
                    "Ecart": f"{dec['effet_cumule'] * 100:+.1f} pt",
                },
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    if is_2024:
        st.subheader("Confrontation a un vote reel : censure du 4 decembre 2024")
        obs = analyze_observed_vote(CENSURE_BARNIER_2024)
        minimale = "minimale" if obs["coalition_minimale"] else "non minimale"
        st.write(
            f"La coalition NFP + RN + UDR totalise {obs['sieges_si_discipline_parfaite']} "
            f"sieges pour {obs['voix_pour_observees']} voix reelles (seuil requis ce "
            f"jour-la : {obs['majorite_requise']}). Coalition gagnante mais {minimale} ; "
            f"groupes reellement critiques : {', '.join(obs['groupes_critiques_observes'])}."
        )
        breakdown = discipline_breakdown(CENSURE_BARNIER_2024)
        st.write(
            f"L'ecart net de {obs['ecart_discipline']} entre sieges et voix ne mesure pas "
            f"directement les defections : il confond {breakdown['defections_internes']} "
            f"defections internes a la coalition et {breakdown['ralliements_externes']} "
            "voix venues de l'exterieur (un non-inscrit, un depute LIOT)."
        )
        st.dataframe(
            breakdown["detail_par_groupe"], use_container_width=True, hide_index=True
        )


elif mode == "Europeennes (D'Hondt)":
    allocation = allocate_2024()
    votes = {p.code: p.votes for p in EUROPEENNES_2024}

    st.subheader("Repartition D'Hondt des 81 sieges (9 juin 2024)")
    st.pyplot(plot_seats_bar(allocation))
    st.pyplot(plot_dhondt_quotients(votes, allocation))

    st.subheader("Pouvoir de vote dans la delegation francaise")
    game = majority_game_europeennes_2024()
    render_game_analysis(game)

    st.divider()
    st.subheader("Impact du mode de scrutin (a suffrages constants)")
    st.write(
        "On garde les memes suffrages et on fait varier la seule regle d'attribution "
        "des sieges : D'Hondt, Sainte-Lague, puis majoritaire integral. Le pouvoir de "
        "pivot du RN passe de pivot a dictateur selon la regle, a voix inchangees."
    )
    st.dataframe(compare_scrutin_modes_2024(), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Seuils strategiques de D'Hondt")
    marginal = dhondt_marginal_votes(votes, SEATS_2024, 0.05)
    st.write(
        f"Le dernier siege s'obtient au quotient frontiere de "
        f"{marginal['quotient_frontiere']:.0f} voix : c'est le prix effectif d'un siege. "
        "Voici, a repartition figee des autres listes, le nombre de suffrages qu'il "
        "aurait fallu a chaque liste pour un siege de plus."
    )
    st.dataframe(
        [
            {"Liste": code, "Voix pour un siege de plus": n}
            for code, n in sorted(marginal["voix_pour_un_siege_de_plus"].items(), key=lambda kv: kv[1])
        ],
        use_container_width=True,
        hide_index=True,
    )


elif mode == "Regionales (prime majoritaire)":
    st.subheader("Regionales 2021 en Ile-de-France : prime majoritaire (209 sieges)")
    st.write(
        "Le scrutin regional attribue un quart des sieges en prime a la liste arrivee "
        "en tete, puis repartit le reste a la plus forte moyenne. C'est le systeme qui "
        "cree les seuils strategiques vises par l'enonce."
    )
    allocation = allocate_idf_2021()
    st.dataframe(
        [{"Liste": code, "Sieges": s} for code, s in allocation.items()],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Pouvoir de vote au conseil regional")
    game = majority_game_regionales_idf_2021()
    render_game_analysis(game)

    st.divider()
    st.subheader("Impact du mode de scrutin (a suffrages constants)")
    st.write(
        "A voix inchangees, la prime majoritaire transforme une pluralite (45,9 % des "
        "voix) en majorite absolue des sieges, donc en dictateur au sens des indices. "
        "La proportionnelle pure ne donnerait au vainqueur qu'un pouvoir de pivot partage."
    )
    st.dataframe(regionales_mode_impact(), use_container_width=True, hide_index=True)


elif mode == "Verification formelle":
    st.subheader("Preuve des axiomes de Shapley-Shubik par Z3")
    st.write(
        "Pour un nombre de joueurs fixe, les valeurs des coalitions deviennent des "
        "variables Z3. Chaque axiome est demontre en etablissant que sa negation est "
        "insatisfaisable (UNSAT). La preuve est bornee : valable pour le n choisi."
    )
    n = st.slider("Nombre de joueurs n", min_value=2, max_value=6, value=4)
    with st.spinner("Resolution Z3 en cours..."):
        results = prove_all_axioms(n)
    rows = [
        {"Axiome": r.axiom, "Prouve": "Oui" if r.proved else "Non", "Detail": r.detail}
        for r in results
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    if all(r.proved for r in results):
        st.success(f"Les quatre axiomes sont demontres pour n = {n}.")

    st.subheader("Preuve des axiomes de Deegan-Packel par Z3")
    st.write(
        "Deegan-Packel n'est pas lineaire en les valeurs des coalitions. On encode le "
        "predicat de coalition gagnante minimale, puis on prouve la symetrie, le joueur "
        "nul et l'efficacite par la meme methode (negation UNSAT), sans division."
    )
    with st.spinner("Resolution Z3 en cours..."):
        dp_results = prove_all_deegan_packel_axioms(n)
    dp_rows = [
        {"Axiome": r.axiom, "Prouve": "Oui" if r.proved else "Non", "Detail": r.detail}
        for r in dp_results
    ]
    st.dataframe(dp_rows, use_container_width=True, hide_index=True)
    if all(r.proved for r in dp_results):
        st.success(f"Les axiomes applicables a Deegan-Packel sont demontres pour n = {n}.")

    st.subheader("Ce qui distingue les trois indices")
    st.write(
        "Seul Shapley-Shubik concilie efficacite et additivite. Banzhaf viole "
        "l'efficacite (Z3 exhibe un contre-exemple) ou l'additivite selon sa "
        "normalisation. C'est la propriete qui separe formellement les indices."
    )
    st.dataframe(axiom_matrix(n), use_container_width=True, hide_index=True)


elif mode == "Validation symbolique":
    st.subheader("Concordance encodage SMT / enumeration combinatoire")
    st.write(
        "Le statut des joueurs, le decompte des swings et les coalitions gagnantes "
        "minimales sont calcules par deux voies independantes (Python explicite et Z3). "
        "Leur concordance garantit la correction du volet symbolique."
    )
    choice = st.selectbox("Instance", list(PREDEFINED))
    game = PREDEFINED[choice]
    checks = cross_validate_smt(game)
    st.dataframe(
        [{"Verification": k, "Concordance": "Oui" if v else "Non"} for k, v in checks.items()],
        use_container_width=True,
        hide_index=True,
    )
    if all(checks.values()):
        st.success("Les deux approches concordent parfaitement.")

    st.subheader("Compromis precision / cout : exact contre Monte Carlo")
    st.dataframe(montecarlo_benchmark(game), use_container_width=True, hide_index=True)
