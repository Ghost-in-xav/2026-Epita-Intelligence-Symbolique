"""Chargement des données de marché, avec repli synthétique.

`load_prices` tente d'abord yfinance. En cas d'échec (pas de réseau, ticker
indisponible), on génère une série **synthétique à régimes connus** : utile hors
ligne, reproductible, et sécurité pour la démo si le wifi lâche en soutenance.
Le mode synthétique renvoie aussi la vraie suite de régimes (`true_regime`),
ce qui permet de mesurer la qualité de la détection.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

REGIMES = ["bear", "range", "bull"]


def load_prices(ticker="SPY", start="2015-01-01", end="2024-12-31",
                force_synthetic=False, seed=2):
    """Retourne (prices, true_regime).

    prices : Series de prix. true_regime : Series (synthétique) ou None (yfinance).
    """
    if not force_synthetic:
        try:
            import yfinance as yf
            df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
            if df is not None and len(df) > 50:
                close = df["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                close.name = ticker
                return close.dropna(), None
        except Exception as exc:
            print(f"[data] yfinance indisponible ({exc}); repli synthétique.")
    return _synthetic_prices(start, end, seed)


def _synthetic_prices(start, end, seed):
    """Marche aléatoire à régimes markoviens (bear/range/bull), marché haussier
    ponctué de crises. Matrice de transition « collante »."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start=start, end=end)
    n = len(dates)
    order = ["bear", "range", "bull"]
    params = {"bear": (-0.0015, 0.022), "range": (0.0000, 0.006), "bull": (0.0009, 0.010)}
    P = np.array([
        [0.950, 0.050, 0.000],
        [0.030, 0.955, 0.015],
        [0.000, 0.010, 0.990],
    ])
    states = np.empty(n, dtype=int)
    states[0] = 2
    for t in range(1, n):
        states[t] = rng.choice(3, p=P[states[t - 1]])
    rets = np.array([rng.normal(*params[order[s]]) for s in states])
    prices = pd.Series(100 * np.exp(np.cumsum(rets)), index=dates, name="SYNTH")
    true_regime = pd.Series([order[s] for s in states], index=dates, name="true_regime")
    return prices, true_regime


def make_features(prices: pd.Series, w_mean: int = 3, w_vol: int = 10) -> pd.DataFrame:
    """Features d'émission : rendement moyen court + volatilité réalisée.

    Le rendement sur fenêtre courte garde de la réactivité (baseline nerveuse),
    la volatilité sépare bear (vol haute) de range (vol basse).
    """
    ret = np.log(prices).diff()
    feats = pd.DataFrame({
        "ret": ret.rolling(w_mean).mean(),
        "vol": ret.rolling(w_vol).std(),
    }).dropna()
    return feats
