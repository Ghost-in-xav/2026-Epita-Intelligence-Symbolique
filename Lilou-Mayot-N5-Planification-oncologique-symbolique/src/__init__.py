"""
onco_plan
=========
Systeme de planification oncologique symbolique (Sujet N5) combinant trois
couches : ontologie OWL/HermiT, contraintes Z3/SMT, et inference
probabiliste PyMC/MCMC.

Modules
-------
ontology_owl
    Ontologie OWL 2 DL (owlready2 + raisonneur HermiT) : agents, protocoles,
    pathologies, contre-indications, classes inferees, verification SPARQL.
smt_planning
    Contraintes Z3/SMT pour la planification des cycles de chimiotherapie
    (espacement, capacite, dose cumulee, compatibilite patient/protocole),
    avec diagnostic d'infaisabilite via unsat_core.
proba_toxicity
    Modele probabiliste PyMC : inference MCMC/NUTS du profil de toxicite
    patient-specifique (melange marginalise sur 3 profils), simulation de
    risque futur et recommandation de dose.
pipeline
    Integration des trois couches en un systeme de recommandation unique
    (PipelineOncoPlan).
validation
    Validation du pipeline sur les 8 patients reels du dataset CoursIA
    Oncology-Planning.
"""

from .ontology_owl import (
    build_ontology,
    populate_ontology,
    run_reasoner,
    verifier_prescription,
    agents_haut_risque,
)
from .smt_planning import (
    construire_modele_planification,
    planifier_chimio,
)
from .proba_toxicity import (
    normaliser_doses,
    calculer_trajectoire_toxicite,
    calculer_trajectoire_toxicite_numpy,
    construire_modele,
    inferer_profil,
    simuler_risque_futur,
    analyse_sensibilite_anc_wbc,
    recommander_dose,
    seuil_wbc_equivalent,
    PROFILS,
    SENSIBILITE_MAP,
    PRIOR_PROFIL,
    SEUIL_CRITIQUE_GB,
    RATIO_ANC_WBC_DEFAUT,
    SEUIL_ANC_NEUTROPENIE_SEVERE,
    SEUIL_ANC_NEUTROPENIE_MODEREE,
    SEUIL_ANC_NEUTROPENIE_LEGERE,
)
from .pipeline import PipelineOncoPlan
from .validation import run_validation

__all__ = [
    # ontology_owl
    "build_ontology", "populate_ontology", "run_reasoner",
    "verifier_prescription", "agents_haut_risque",
    # smt_planning
    "construire_modele_planification", "planifier_chimio",
    # proba_toxicity
    "normaliser_doses", "calculer_trajectoire_toxicite",
    "calculer_trajectoire_toxicite_numpy", "construire_modele",
    "inferer_profil", "simuler_risque_futur", "analyse_sensibilite_anc_wbc",
    "recommander_dose",
    "seuil_wbc_equivalent",
    "PROFILS", "SENSIBILITE_MAP", "PRIOR_PROFIL", "SEUIL_CRITIQUE_GB",
    "RATIO_ANC_WBC_DEFAUT", "SEUIL_ANC_NEUTROPENIE_SEVERE",
    "SEUIL_ANC_NEUTROPENIE_MODEREE", "SEUIL_ANC_NEUTROPENIE_LEGERE",
    # pipeline
    "PipelineOncoPlan",
    # validation
    "run_validation",
]
