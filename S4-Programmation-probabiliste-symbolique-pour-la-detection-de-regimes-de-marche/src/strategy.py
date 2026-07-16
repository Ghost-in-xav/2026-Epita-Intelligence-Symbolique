"""Couche stratégie + backtest local (avec coûts de transaction).

Objectif S4 #4 : allocation multi-régime (poids selon le régime).
Objectif S4 #5 : backtest et comparaison vs HMM pur et vs buy-and-hold.

Allocation (1 actif risqué) :  bull -> 100% | range -> 50% | bear -> 0% (cash)

Backtest local (pandas), avec coûts de transaction proportionnels au turnover.
Les coûts sont essentiels : ils pénalisent les stratégies qui « clignotent »,
ce qui met en valeur la stabilisation apportée par les couches symboliques.
Exposition décalée d'un jour (pas de look-ahead).

Note : l'énoncé mentionne QuantConnect Lean ; on reste ici sur un backtest local
pour la simplicité. Le régime déduit se branche tel quel sur un alpha QC.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

EXPOSURE = {"bull": 1.0, "range": 0.5, "bear": 0.0}
TRADING_DAYS = 252


def exposures(regimes: pd.Series) -> pd.Series:
    return regimes.map(EXPOSURE).astype(float)


def backtest(returns: pd.Series, regimes: pd.Series, cost: float = 0.0010) -> pd.Series:
    """Courbe d'équité d'une stratégie régime -> exposition, coûts inclus.

    cost : coût par unité de turnover (0.0010 = 10 bps).
    """
    expo = exposures(regimes).reindex(returns.index).ffill().fillna(0.0)
    turnover = expo.diff().abs().fillna(0.0)
    strat_ret = expo.shift(1).fillna(0.0) * returns - turnover * cost
    return (1.0 + strat_ret).cumprod()


def buy_and_hold(returns: pd.Series) -> pd.Series:
    return (1.0 + returns).cumprod()


def n_trades(regimes: pd.Series, returns: pd.Series) -> int:
    expo = exposures(regimes).reindex(returns.index).ffill().fillna(0.0)
    return int((expo.diff().abs() > 0).sum())


def metrics(equity: pd.Series) -> dict:
    ret = equity.pct_change().dropna()
    total = equity.iloc[-1] / equity.iloc[0] - 1.0
    sharpe = np.sqrt(TRADING_DAYS) * ret.mean() / ret.std() if ret.std() > 0 else np.nan
    mdd = (equity / equity.cummax() - 1.0).min()
    return {
        "rendement_total": round(float(total), 3),
        "sharpe": round(float(sharpe), 2),
        "max_drawdown": round(float(mdd), 3),
    }


def compare(returns: pd.Series, regimes_by_method: dict, cost: float = 0.0010):
    """Backteste plusieurs jeux de régimes + buy-and-hold.

    Renvoie (table_metrics, courbes_equity).
    """
    rows, curves = {}, {}
    for name, reg in regimes_by_method.items():
        eq = backtest(returns, reg, cost)
        curves[name] = eq
        m = metrics(eq)
        m["trades"] = n_trades(reg, returns)
        rows[name] = m
    bh = buy_and_hold(returns)
    curves["buy_and_hold"] = bh
    m = metrics(bh); m["trades"] = 0
    rows["buy_and_hold"] = m
    cols = ["rendement_total", "sharpe", "max_drawdown", "trades"]
    return pd.DataFrame(rows).T[cols], curves
