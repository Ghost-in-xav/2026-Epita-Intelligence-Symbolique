"""S4 — détection hybride symbolique-probabiliste de régimes de marché.

Pipeline :
    prix -> features -> HMM (couche 1) -> révision AGM (couche 2)
         -> transitions qualitatives (couche 3) -> allocation + backtest.
"""
from . import data, hmm, agm, qualitative, strategy
