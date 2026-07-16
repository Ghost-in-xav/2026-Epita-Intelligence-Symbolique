"""
visualization.py
=================
Visualisations du systeme OncoPlan-Symbolique (Sujet N5).

Fonctions
---------
plot_dataset_exploration
    Trajectoires de globules blancs et scores de toxicite par patient.
plot_agent_toxicity_heatmap
    Profil de toxicite par agent, groupe par famille pharmacologique.
plot_mcmc_trace
    Diagnostic de convergence MCMC (trace plot ArviZ) pour un patient.
plot_anc_wbc_sensitivity
    Sensibilite de la decision de dose au ratio ANC/WBC suppose.
plot_patient_risk_map
    Carte de risque croisant statut pipeline, profil estime et p_danger.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from typing import Optional, Sequence


# ── Palette ──────────────────────────────────────────────────────────────────

COLORS_STATUT = {
    "VALIDE": "#2ca02c",
    "VALIDE_DOSE_AJUSTEE": "#ff7f0e",
    "REPORT_RECOMMANDE": "#d62728",
    "REFUSE": "#7f0000",
}


def _apply_style(ax: plt.Axes) -> None:
    """Style minimal : pas de cadre haut/droite, grille legere."""
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(True, alpha=0.3)


# ─────────────────────────────────────────────────────────────────────────────

def plot_dataset_exploration(
    df: pd.DataFrame,
    seuil_danger: float = 1500.0,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Trace les trajectoires de globules blancs et le score de toxicite max
    par patient, pour une exploration rapide du dataset.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset patients_oncology.csv charge (colonnes patient_id,
        cycle_numero, jour_cycle, taux_globules_blancs, score_toxicite,
        hospitalisation).
    seuil_danger : float, optional
        Seuil de danger (WBC total) a tracer en reference. Defaut : 1500.
    save_path : str, optional
        Chemin de sauvegarde de la figure (PNG). Si None, non sauvegardee.

    Returns
    -------
    plt.Figure
    """
    summary = df.groupby("patient_id")["score_toxicite"].max()
    hosp = df.groupby("patient_id")["hospitalisation"].apply(lambda x: (x == "Oui").any())

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))

    for pid, grp in df.groupby("patient_id"):
        grp = grp.sort_values(["cycle_numero", "jour_cycle"])
        t = range(len(grp))
        style = "-o" if (grp["hospitalisation"] == "Oui").any() else "--o"
        axes[0].plot(t, grp["taux_globules_blancs"], style, label=pid, alpha=0.8)

    axes[0].axhline(seuil_danger, color="red", linestyle=":", label="Seuil de danger (WBC)")
    axes[0].set_title("Trajectoires des globules blancs\n(trait plein = patient hospitalise)",
                       fontweight="bold")
    axes[0].set_xlabel("Pas de temps (J1C1, J8C1, J15C1, J21C1, J1C2, ...)")
    axes[0].set_ylabel("Taux de globules blancs (/uL)")
    axes[0].legend(fontsize=8, ncol=2)
    _apply_style(axes[0])

    axes[1].bar(summary.index, summary.values,
                color=["crimson" if h else "steelblue" for h in hosp])
    axes[1].set_title("Score de toxicite max par patient\n(rouge = hospitalise)",
                       fontweight="bold")
    axes[1].set_ylabel("Score de toxicite (0-5)")
    _apply_style(axes[1])

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=120, bbox_inches="tight")
    return fig


def plot_agent_toxicity_heatmap(
    onto,
    familles: Optional[Sequence[str]] = None,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Trace une heatmap du profil de toxicite (renal/cardiaque/neuro/hemato)
    pour chaque agent de l'ontologie, groupe par famille pharmacologique.

    Parameters
    ----------
    onto : owlready2 Ontology
        Ontologie deja construite et peuplee (cf. ontology_owl.build_ontology
        / populate_ontology).
    familles : sequence of str, optional
        Noms des classes de familles pharmacologiques a parcourir. Par
        defaut, les 9 familles disjointes du module ontology_owl.
    save_path : str, optional
        Chemin de sauvegarde de la figure (PNG). Si None, non sauvegardee.

    Returns
    -------
    plt.Figure
    """
    if familles is None:
        familles = ["AgentPlatine", "Taxane", "VincaAlcaloide", "Anthracycline",
                    "Antimetabolite", "AnticorpsMonoclonal", "TopoisomeraseInhibiteur",
                    "AgentAlkylant", "Corticosteroide"]

    lignes_agents = []
    for famille in familles:
        cls = getattr(onto, famille)
        for agent in cls.instances():
            lignes_agents.append({
                "agent": agent.name,
                "famille": famille,
                "renale": bool(agent.toxicite_renale),
                "cardiaque": bool(agent.toxicite_cardiaque),
                "neuro": bool(agent.toxicite_neurologique),
                "hemato": bool(agent.toxicite_hematologique),
                "dose_max": agent.dose_cumulee_max_mg_m2,
            })

    df_agents = pd.DataFrame(lignes_agents).sort_values(["famille", "agent"]).reset_index(drop=True)
    toxicite_labels = ["Renale", "Cardiaque", "Neuro", "Hemato"]

    fig, ax = plt.subplots(figsize=(9, max(6, 0.4 * len(df_agents))))
    mat = df_agents[["renale", "cardiaque", "neuro", "hemato"]].astype(int).values
    im = ax.imshow(mat, cmap="Reds", aspect="auto", vmin=0, vmax=1)

    ax.set_yticks(range(len(df_agents)))
    ax.set_yticklabels(df_agents["agent"] + df_agents["dose_max"].apply(
        lambda d: " *" if pd.notna(d) else ""
    ))
    ax.set_xticks(range(4))
    ax.set_xticklabels(toxicite_labels)

    prev_famille = None
    for i, fam in enumerate(df_agents["famille"]):
        if prev_famille is not None and fam != prev_famille:
            ax.axhline(i - 0.5, color="black", linewidth=0.8)
        prev_famille = fam

    ax.set_title("Profil de toxicite par agent, groupe par famille pharmacologique\n"
                 "(* = seuil de dose cumulee documente)", fontweight="bold")
    plt.colorbar(im, ax=ax, label="Toxicite assertee (0/1)", shrink=0.6)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=120, bbox_inches="tight")
    return fig, df_agents


def plot_mcmc_trace(idata, var_names=("poids_profil",), patient_label="",
                     save_path: Optional[str] = None):
    """
    Trace le diagnostic de convergence MCMC (trace plot ArviZ) pour les
    poids du melange (profil de toxicite latent) d'un patient.

    Parameters
    ----------
    idata : arviz.InferenceData
        Resultat d'inference PyMC (cf. proba_toxicity.inferer_profil,
        cle "idata" du dict retourne).
    var_names : sequence of str, optional
        Variables a tracer. Defaut : ("poids_profil",).
    patient_label : str, optional
        Libelle du patient/protocole a afficher dans le titre.
    save_path : str, optional
        Chemin de sauvegarde de la figure (PNG). Si None, non sauvegardee.

    Returns
    -------
    np.ndarray
        Tableau d'axes matplotlib (retour natif de az.plot_trace).
    """
    import arviz as az

    axes = az.plot_trace(idata, var_names=list(var_names))
    fig = plt.gcf()
    fig.suptitle(f"Diagnostic de convergence MCMC -- poids du melange "
                 f"(profil de toxicite){chr(10)}{patient_label}", y=1.02,
                 fontweight="bold")
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=120, bbox_inches="tight")
    return axes


def plot_anc_wbc_sensitivity(
    sensibilites: dict,
    seuil_decision: float = 0.05,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Trace la sensibilite de P(danger) au ratio ANC/WBC suppose, pour un ou
    plusieurs patients (cf. proba_toxicity.analyse_sensibilite_anc_wbc).

    Parameters
    ----------
    sensibilites : dict[str, list[dict]]
        Mapping {libelle_patient: resultat de analyse_sensibilite_anc_wbc}.
        Chaque resultat est une liste de dicts avec les cles
        "ratio_anc_wbc" et "p_danger".
    seuil_decision : float, optional
        Seuil de risque acceptable a tracer en reference. Defaut : 0.05.
    save_path : str, optional
        Chemin de sauvegarde de la figure (PNG). Si None, non sauvegardee.

    Returns
    -------
    plt.Figure
    """
    fig, ax = plt.subplots(figsize=(8, 5))
    marqueurs = ["o", "s", "^", "D", "v"]

    for (label, resultat), marqueur in zip(sensibilites.items(), marqueurs):
        df_sens = pd.DataFrame(resultat)
        ax.plot(df_sens["ratio_anc_wbc"], df_sens["p_danger"], f"{marqueur}-", label=label)

    ax.axhline(seuil_decision, color="red", linestyle=":",
               label=f"Seuil de decision ({seuil_decision:.0%})")
    ax.set_xlabel("Ratio ANC/WBC suppose")
    ax.set_ylabel("P(danger) estimee")
    ax.set_title("Sensibilite de la decision au ratio ANC/WBC\n"
                 "(hypothese clinique non observable directement dans le dataset)",
                 fontweight="bold")
    ax.legend()
    _apply_style(ax)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=120, bbox_inches="tight")
    return fig


def plot_patient_risk_map(
    resultats_validation: pd.DataFrame,
    seuil_decision: float = 0.05,
    save_path: Optional[str] = None,
) -> plt.Figure:
    """
    Trace une carte de risque croisant, pour chaque patient, le statut
    final du pipeline, le profil de toxicite estime, et P(danger).

    Parameters
    ----------
    resultats_validation : pd.DataFrame
        Resultat de validation.run_validation() (colonnes patient,
        statut_pipeline, profil_estime, p_danger, hospitalise_reel).
    seuil_decision : float, optional
        Seuil de risque acceptable a tracer en reference. Defaut : 0.05.
    save_path : str, optional
        Chemin de sauvegarde de la figure (PNG). Si None, non sauvegardee.

    Returns
    -------
    plt.Figure
    """
    fig, ax = plt.subplots(figsize=(9, 5))
    ordre = resultats_validation.sort_values("p_danger", ascending=True)

    ax.barh(
        ordre["patient"], ordre["p_danger"],
        color=[COLORS_STATUT.get(s, "gray") for s in ordre["statut_pipeline"]],
    )
    ax.axvline(seuil_decision, color="black", linestyle=":",
               label=f"Seuil de decision ({seuil_decision:.0%})")

    for i, (_, row) in enumerate(ordre.iterrows()):
        marqueur = " (hospitalise)" if row["hospitalise_reel"] else ""
        ax.text(row["p_danger"] + 0.01, i,
                f"{row['profil_estime']}{marqueur}", va="center", fontsize=9)

    ax.set_xlabel("P(danger) estimee")
    ax.set_title("Carte de risque par patient\n(couleur = statut final du pipeline)",
                 fontweight="bold")
    ax.set_xlim(0, max(ordre["p_danger"].max() * 1.4, 0.1))
    _apply_style(ax)

    legend_elements = [Patch(facecolor=c, label=s) for s, c in COLORS_STATUT.items()
                        if s in resultats_validation["statut_pipeline"].values]
    seuil_line = ax.get_legend_handles_labels()
    ax.legend(handles=legend_elements + list(seuil_line[0][-1:]),
              loc="lower right", fontsize=8)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=120, bbox_inches="tight")
    return fig
