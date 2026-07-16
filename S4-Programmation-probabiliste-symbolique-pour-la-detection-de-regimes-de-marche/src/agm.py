"""Couche 2 — Révision des croyances AGM (version opérationnelle simple).

Objectif S4 #2 : maintenir une croyance sur le régime courant et la mettre à
jour symboliquement face aux observations, au lieu de suivre l'argmax bruité
du HMM (qui « clignote »).

Lecture AGM (Alchourrón, Gärdenfors, Makinson 1985). La base de croyances est
réduite ici à une seule proposition : « le régime courant est R ». À chaque pas
on reçoit une évidence (le posterior du HMM) et on applique :

- **Expansion** : si l'évidence est cohérente avec la croyance courante
  (le régime cru reste le plus probable, ou l'écart est faible), on garde R
  — principe de *changement minimal*.
- **Révision** : on ne remplace R par un nouveau régime R' que si l'évidence
  contredisant R est à la fois **forte** (proba de R' >= `conf`) et
  **persistante** (R' est l'argmax depuis >= `persistence` jours). Cela
  respecte le *succès* (on finit par accepter une évidence forte et stable)
  tout en évitant les révisions sur du bruit.

C'est une opérationnalisation simplifiée, pas une algèbre AGM complète : on la
présente comme telle. L'effet net attendu : des régimes beaucoup plus stables
que le HMM pur.
"""
from __future__ import annotations

import pandas as pd

REGIMES = ["bear", "range", "bull"]


def revise_beliefs(
    proba: pd.DataFrame,
    conf: float = 0.60,
    persistence: int = 3,
) -> pd.Series:
    """Applique la révision AGM sur la suite des posteriors HMM.

    Args:
        proba: DataFrame [dates x REGIMES] des probabilités a posteriori.
        conf: seuil de confiance pour accepter un changement de régime.
        persistence: nb de jours consécutifs où le candidat doit dominer.

    Returns:
        Series des régimes *crus* après révision.
    """
    argmax = proba.idxmax(axis=1)
    top = proba.max(axis=1)
    dates = proba.index

    believed = []
    current = argmax.iloc[0]
    streak_regime = current
    streak_len = 0

    for i, date in enumerate(dates):
        cand = argmax.iloc[i]
        if cand == streak_regime:
            streak_len += 1
        else:
            streak_regime = cand
            streak_len = 1

        if cand == current:
            pass
        else:
            if top.iloc[i] >= conf and streak_len >= persistence:
                current = cand

        believed.append(current)

    return pd.Series(believed, index=dates, name="agm")
