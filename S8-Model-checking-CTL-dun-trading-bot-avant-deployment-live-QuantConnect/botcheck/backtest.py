from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from .monitor import InvariantMonitor
from .strategy import (DD_CRIT, DD_WARN, BotState, next_leverage, next_mode,
                       next_profit)

def drawdown_bucket(dd_pct: float) -> int:
    if dd_pct >= 0.20:
        return 3
    if dd_pct >= 0.15:
        return 2
    if dd_pct >= 0.05:
        return 1
    return 0

@dataclass
class BacktestConfig:
    fast_window: int = 20
    slow_window: int = 50
    take_profit_pct: float = 0.10
    halt_return_threshold: float = -0.08
    initial_equity: float = 100_000.0

@dataclass
class BacktestResult:
    equity_curve: List[float] = field(default_factory=list)
    states: List[BotState] = field(default_factory=list)
    monitor: InvariantMonitor = field(default_factory=InvariantMonitor)
    n_bars: int = 0
    max_drawdown: float = 0.0
    final_equity: float = 0.0

    def summary(self) -> str:
        ret = (self.final_equity / self.equity_curve[0] - 1) * 100 if self.equity_curve else 0
        return (f"[BACKTEST] {self.n_bars} barres | equity finale "
                f"{self.final_equity:,.0f} ({ret:+.1f}%) | max drawdown "
                f"{self.max_drawdown*100:.1f}%\n{self.monitor.report()}")

def _sma(prices: Sequence[float], end: int, window: int) -> Optional[float]:
    if end + 1 < window:
        return None
    return sum(prices[end + 1 - window: end + 1]) / window

def _derive_signal(prices, i, cfg, mode, entry_price) -> str:
    if i > 0:
        bar_ret = prices[i] / prices[i - 1] - 1
        if bar_ret <= cfg.halt_return_threshold:
            return "halt"

    if mode in ("long", "short") and entry_price:
        pnl = (prices[i] / entry_price - 1) * (1 if mode == "long" else -1)
        if pnl >= cfg.take_profit_pct:
            return "tp"
    fast = _sma(prices, i, cfg.fast_window)
    slow = _sma(prices, i, cfg.slow_window)
    prev_fast = _sma(prices, i - 1, cfg.fast_window) if i > 0 else None
    prev_slow = _sma(prices, i - 1, cfg.slow_window) if i > 0 else None
    if None in (fast, slow, prev_fast, prev_slow):
        return "hold"
    crossed_up = prev_fast <= prev_slow and fast > slow
    crossed_down = prev_fast >= prev_slow and fast < slow
    if crossed_up:
        return "buy"
    if crossed_down:
        return "sell"
    return "hold"

def run_backtest(prices: Sequence[float], cfg: Optional[BacktestConfig] = None
                 ) -> BacktestResult:
    cfg = cfg or BacktestConfig()
    res = BacktestResult()
    mon = res.monitor

    equity = cfg.initial_equity
    peak = equity
    mode, leverage, profit = "flat", 0, False
    entry_price: Optional[float] = None

    for i in range(len(prices)):
        if i > 0 and mode in ("long", "short") and leverage > 0:
            r = prices[i] / prices[i - 1] - 1
            direction = 1 if mode == "long" else -1
            equity *= (1 + direction * leverage * r)
        peak = max(peak, equity)
        dd_pct = (peak - equity) / peak if peak > 0 else 0.0
        res.max_drawdown = max(res.max_drawdown, dd_pct)
        dd = drawdown_bucket(dd_pct)

        signal = _derive_signal(prices, i, cfg, mode, entry_price)
        cur = BotState(mode=mode, signal=signal, drawdown=dd,
                       leverage=leverage, profit=profit)
        mon.observe(cur)
        res.states.append(cur)
        res.equity_curve.append(equity)

        nmode = next_mode(cur)
        nlev = next_leverage(cur, nmode)
        nprofit = next_profit(cur)
        if nmode in ("long", "short") and mode == "flat":
            entry_price = prices[i]
        elif nmode == "flat":
            entry_price = None
        mode, leverage, profit = nmode, nlev, nprofit

    res.n_bars = len(prices)
    res.final_equity = equity
    return res

def synthetic_prices(n: int = 1260, seed: int = 42, mu: float = 0.0003,
                     sigma: float = 0.012, shock_prob: float = 0.01) -> List[float]:
    rng = random.Random(seed)
    price = 100.0
    out = [price]
    for _ in range(n - 1):
        shock = -abs(rng.gauss(0.06, 0.03)) if rng.random() < shock_prob else 0.0
        ret = rng.gauss(mu, sigma) + shock
        price *= math.exp(ret)
        out.append(max(0.01, price))
    return out
