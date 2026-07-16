"""Couche 1 — Détection probabiliste des régimes (HMM gaussien).

Objectif S4 #1 : détecter numériquement les régimes et exposer une distribution
de probabilité sur le régime courant.

On utilise `hmmlearn.GaussianHMM`. Les états sont anonymes (0,1,2) : on les
étiquette bear/range/bull en les triant par rendement moyen.

Deux "vues" de la probabilité de régime :
- `emission_proba` : probabilité fondée sur la seule émission du jour (on ignore
  la dynamique temporelle). C'est l'évidence *instantanée* — bruitée. Elle sert
  à la fois de baseline "HMM pur" (argmax) et d'entrée à la couche AGM, qui lui
  ajoute justement le raisonnement temporel qui lui manque.
- `smoothed_proba` : posterior lissé par forward-backward (predict_proba), utile
  pour les graphiques.

Ressource : Probas/PyMC-HMM-Trading-Alpha.ipynb.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from scipy.stats import norm

REGIMES = ["bear", "range", "bull"]


def fit_hmm(features: pd.DataFrame, n_states: int = 3, n_restarts: int = 8) -> GaussianHMM:
    """Ajuste un HMM gaussien ; garde le meilleur de plusieurs initialisations.

    Le multi-restart évite les optima locaux dégénérés d'EM.
    """
    best, best_score = None, -np.inf
    for seed in range(n_restarts):
        m = GaussianHMM(n_components=n_states, covariance_type="diag",
                        n_iter=200, tol=1e-3, random_state=seed)
        try:
            m.fit(features.values)
            score = m.score(features.values)
        except Exception:
            continue
        if score > best_score:
            best, best_score = m, score
    if best is None:
        raise RuntimeError("Échec de l'ajustement du HMM.")
    return best


def label_map(model: GaussianHMM, ret_col: int = 0) -> dict:
    """État HMM -> régime, en triant par rendement moyen (bas=bear, haut=bull)."""
    order = np.argsort(model.means_[:, ret_col])
    return {int(state): REGIMES[rank] for rank, state in enumerate(order)}


def _diag_var(model: GaussianHMM, k: int) -> np.ndarray:
    cov = model.covars_[k]
    return cov.diagonal() if cov.ndim == 2 else cov


def emission_proba(model: GaussianHMM, features: pd.DataFrame) -> pd.DataFrame:
    """Probabilité de régime fondée sur la seule émission du jour (sans dynamique).

    Évidence instantanée -> bruitée. C'est l'entrée de la couche AGM.
    """
    logp = np.zeros((len(features), model.n_components))
    for k in range(model.n_components):
        logp[:, k] = norm.logpdf(features.values, model.means_[k],
                                 np.sqrt(_diag_var(model, k))).sum(axis=1)
    logp -= logp.max(axis=1, keepdims=True)
    p = np.exp(logp)
    p /= p.sum(axis=1, keepdims=True)
    lab = label_map(model)
    cols = {lab[k]: p[:, k] for k in range(model.n_components)}
    return pd.DataFrame(cols, index=features.index)[REGIMES]


def smoothed_proba(model: GaussianHMM, features: pd.DataFrame) -> pd.DataFrame:
    """Posterior lissé (forward-backward). Pour visualisation."""
    p = model.predict_proba(features.values)
    lab = label_map(model)
    cols = {lab[k]: p[:, k] for k in range(model.n_components)}
    return pd.DataFrame(cols, index=features.index)[REGIMES]


def naive_regimes(model: GaussianHMM, features: pd.DataFrame) -> pd.Series:
    """« HMM pur » = argmax de l'émission jour par jour. Baseline (bruitée)."""
    return emission_proba(model, features).idxmax(axis=1).rename("hmm_pur")
