"""
Pipeline d'integration OncoPlan-Symbolique (Sujet N5).

Chaine les trois couches symboliques/probabilistes en un seul systeme de
recommandation :

    1. Ontologie (OWL + HermiT)   -> verification des contre-indications
    2. Z3 / SMT                    -> planification sous contraintes cliniques
    3. PyMC (MCMC/NUTS)             -> estimation du profil patient-specifique
    4. Decision                    -> recommandation finale (dates, doses)

Chaque etape peut interrompre le pipeline avec une explication ciblee :
- L'ontologie bloque si une contre-indication absolue existe.
- Le solveur Z3 explique (via unsat_core) pourquoi aucun calendrier valide
  n'existe, si c'est le cas.
- PyMC ajuste la dose si le risque estime depasse le seuil acceptable.
"""

from .ontology_owl import (
    build_ontology, populate_ontology, run_reasoner, verifier_prescription
)
from .smt_planning import planifier_chimio
from .proba_toxicity import inferer_profil, recommander_dose


class PipelineOncoPlan:
    """Orchestre les trois couches pour produire une recommandation de
    traitement complete pour un patient donne."""

    def __init__(self):
        self.onto = build_ontology()
        self.refs = populate_ontology(self.onto)
        run_reasoner(self.onto)

    def recommander(self, protocole_nom, patient_pathologies,
                     doses_historique, observations_gb, dose_prevue,
                     occupations_existantes=None, nb_cycles=4,
                     dose_par_cycle=None, verbose=True):
        """Execute le pipeline complet de decision pour un patient.

        Args:
            protocole_nom: nom du protocole envisage (cle de
                refs["protocoles"], ex: "FOLFOX").
            patient_pathologies: liste de comorbidites du patient (cles de
                refs["pathologies"]).
            doses_historique: array des doses deja administrees (mg).
            observations_gb: array des taux de GB observes (meme longueur
                que doses_historique).
            dose_prevue: dose prevue pour la prochaine administration (mg).
            occupations_existantes: dict {jour: charge} pour la
                planification Z3.
            nb_cycles: nombre de cycles a planifier.
            dose_par_cycle: dose de reference par cycle pour le calcul de
                la dose cumulee (par defaut = dose_prevue).
            verbose: si True, affiche chaque etape du pipeline.

        Returns:
            dict structure decrivant le resultat a chaque etape et la
            recommandation finale. En cas d'entree invalide, le dict
            contient {"statut_final": "ERREUR_ENTREE", "raison": ...} au
            lieu de laisser une exception remonter brute -- le pipeline
            orchestre 3 couches developpees independamment, et une entree
            invalide pour l'une d'elles (ex: protocole inconnu pour
            l'ontologie, dose negative pour Z3) doit etre rapportee avec
            le contexte de la couche origine, pas comme un simple
            KeyError/ValueError sans contexte.
        """
        dose_par_cycle = dose_par_cycle if dose_par_cycle is not None else dose_prevue
        resultat = {"protocole": protocole_nom, "etapes": {}}

        def log(msg):
            if verbose:
                print(msg)

        # ------------------------------------------------------------
        # ETAPE 1 : Ontologie -- verification des contre-indications
        # ------------------------------------------------------------
        log(f"\n[1/3] Verification ontologique ({protocole_nom}, "
            f"pathologies={patient_pathologies})...")
        try:
            alertes = verifier_prescription(
                self.onto, self.refs, protocole_nom, patient_pathologies
            )
        except ValueError as e:
            log(f"   -> ENTREE INVALIDE : {e}")
            resultat["statut_final"] = "ERREUR_ENTREE"
            resultat["raison"] = f"Etape ontologie : {e}"
            return resultat
        patient_compatible = len(alertes) == 0
        resultat["etapes"]["ontologie"] = {
            "alertes": alertes,
            "compatible": patient_compatible,
        }

        if not patient_compatible:
            log(f"   -> BLOQUE : {alertes}")
            resultat["statut_final"] = "REFUSE"
            resultat["raison"] = (
                "Contre-indication(s) detectee(s) par l'ontologie : "
                + " | ".join(alertes)
            )
            return resultat
        log("   -> OK, aucune contre-indication.")

        # ------------------------------------------------------------
        # ETAPE 2 : Z3/SMT -- planification sous contraintes
        # ------------------------------------------------------------
        log("\n[2/3] Planification SMT (Z3)...")

        # Recuperer le seuil de dose cumulee depuis l'ontologie (le plus
        # restrictif parmi les agents du protocole, s'il y en a un)
        protocole_obj = self.refs["protocoles"][protocole_nom]
        seuils_dose = [
            a.dose_cumulee_max_mg_m2 for a in protocole_obj.contient_agent
            if a.dose_cumulee_max_mg_m2 is not None
        ]
        dose_max_cumulee = min(seuils_dose) if seuils_dose else None

        try:
            res_smt = planifier_chimio(
                nb_cycles=nb_cycles,
                occupations_existantes=occupations_existantes or {},
                patient_compatible=True,  # deja verifie a l'etape 1
                dose_par_cycle=dose_par_cycle,
                dose_max_cumulee=dose_max_cumulee,
            )
        except ValueError as e:
            log(f"   -> ENTREE INVALIDE : {e}")
            resultat["statut_final"] = "ERREUR_ENTREE"
            resultat["raison"] = f"Etape SMT (Z3) : {e}"
            return resultat
        resultat["etapes"]["smt"] = res_smt

        if res_smt["statut"] != "sat":
            log(f"   -> INFAISABLE : {res_smt.get('unsat_core')}")
            resultat["statut_final"] = "INFAISABLE"
            resultat["raison"] = (
                "Aucun calendrier valide trouve. Contraintes en conflit : "
                + ", ".join(res_smt.get("unsat_core", []))
            )
            return resultat
        log(f"   -> Calendrier valide trouve : {res_smt['calendrier']}")

        # ------------------------------------------------------------
        # ETAPE 3 : PyMC -- inference du profil et ajustement de dose
        # ------------------------------------------------------------
        log("\n[3/3] Inference probabiliste (PyMC/NUTS)...")
        # dose_par_cycle sert de dose de reference du protocole pour la
        # normalisation des doses (cf. onco_pymc.normaliser_doses) : evite
        # de conflater la magnitude de dose propre au protocole avec la
        # sensibilite propre au patient.
        try:
            infer = inferer_profil(doses_historique, observations_gb, dose_par_cycle)
            reco_dose = recommander_dose(
                infer["probs_posterior"], doses_historique, dose_prevue, dose_par_cycle
            )
        except ValueError as e:
            log(f"   -> ENTREE INVALIDE : {e}")
            resultat["statut_final"] = "ERREUR_ENTREE"
            resultat["raison"] = f"Etape probabiliste (PyMC) : {e}"
            return resultat
        resultat["etapes"]["pymc"] = {
            "probs_posterior": {
                p: float(v) for p, v in zip(
                    ["Resistant", "Normal", "Sensible"], infer["probs_posterior"]
                )
            },
            "profil_probable": infer["profil_probable"],
            "rhat_max": infer["rhat_max"],
            "recommandation_dose": reco_dose,
        }
        log(f"   -> Profil estime : {infer['profil_probable']} "
            f"(R-hat={infer['rhat_max']:.4f})")
        log(f"   -> {reco_dose['decision']} (P(danger)={reco_dose['p_danger']:.3f})")

        # ------------------------------------------------------------
        # Decision finale
        # ------------------------------------------------------------
        if reco_dose["dose_recommandee"] <= 0:
            resultat["statut_final"] = "REPORT_RECOMMANDE"
        elif reco_dose["reduction_pct"] > 0:
            resultat["statut_final"] = "VALIDE_DOSE_AJUSTEE"
        else:
            resultat["statut_final"] = "VALIDE"

        resultat["calendrier_propose"] = res_smt["calendrier"]
        resultat["dose_recommandee_mg"] = reco_dose["dose_recommandee"]
        resultat["decision_dose"] = reco_dose["decision"]

        return resultat


if __name__ == "__main__":
    import os
    import pandas as pd

    _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
    pipeline = PipelineOncoPlan()
    df = pd.read_csv(os.path.join(_THIS_DIR, "..", "data", "patients_oncology.csv"))

    print("=" * 70)
    print("CAS 1 : P001 (FOLFOX), patient sans comorbidite connue")
    print("=" * 70)
    p1 = df[df.patient_id == "P001"].sort_values(["cycle_numero", "jour_cycle"])
    res1 = pipeline.recommander(
        protocole_nom="FOLFOX",
        patient_pathologies=[],
        doses_historique=p1["dose_reelle_mg"].values[:6].astype(float),
        observations_gb=p1["taux_globules_blancs"].values[:6].astype(float),
        dose_prevue=85.0,
        occupations_existantes={10: 3, 11: 3, 12: 3},
    )
    print("\n>>> Resultat final :", res1["statut_final"])

    print("\n\n" + "=" * 70)
    print("CAS 2 : P004 (Cisplatin-Vinorelbine), patient insuffisant renal")
    print("=" * 70)
    p4 = df[df.patient_id == "P004"].sort_values(["cycle_numero", "jour_cycle"])
    res2 = pipeline.recommander(
        protocole_nom="Cisplatin-Vinorelbine",
        patient_pathologies=["InsuffisanceRenale"],
        doses_historique=p4["dose_reelle_mg"].values[:6].astype(float),
        observations_gb=p4["taux_globules_blancs"].values[:6].astype(float),
        dose_prevue=75.0,
    )
    print("\n>>> Resultat final :", res2["statut_final"])
    print(">>> Raison :", res2.get("raison"))

    print("\n\n" + "=" * 70)
    print("CAS 3 : P004, meme patient mais protocole Gemcitabine-nab-Paclitaxel "
          "(pas de contre-indication renale connue), forte occupation hopital")
    print("=" * 70)
    res3 = pipeline.recommander(
        protocole_nom="Gemcitabine-nab-Paclitaxel",
        patient_pathologies=["InsuffisanceRenale"],
        doses_historique=p4["dose_reelle_mg"].values[:6].astype(float),
        observations_gb=p4["taux_globules_blancs"].values[:6].astype(float),
        dose_prevue=75.0,
        occupations_existantes={i: 3 for i in range(1, 9)},
    )
    print("\n>>> Resultat final :", res3["statut_final"])
