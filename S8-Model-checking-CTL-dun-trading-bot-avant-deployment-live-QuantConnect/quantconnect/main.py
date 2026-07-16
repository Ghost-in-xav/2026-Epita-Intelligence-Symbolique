from AlgorithmImports import *

MAX_LEVERAGE = 2
DD_WARN = 0.15
DD_CRIT = 0.20
HALT_BAR_RETURN = -0.08
TAKE_PROFIT = 0.10

class CertifiedTrendFollowingBot(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2019, 1, 1)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(100_000)

        equity = self.AddEquity("SPY", Resolution.Daily)
        equity.SetLeverage(MAX_LEVERAGE)
        self.symbol = equity.Symbol

        self.fast = self.SMA(self.symbol, 20, Resolution.Daily)
        self.slow = self.SMA(self.symbol, 50, Resolution.Daily)
        self.SetWarmUp(50)

        self.mode = "flat"
        self.entry_price = None
        self.peak_equity = self.Portfolio.TotalPortfolioValue
        self.prev_fast = None
        self.prev_slow = None

        self.violations = 0

    def OnData(self, data: Slice):
        if self.IsWarmingUp or not self.fast.IsReady or not self.slow.IsReady:
            return
        if not data.ContainsKey(self.symbol) or data[self.symbol] is None:
            return

        price = data[self.symbol].Close
        equity = self.Portfolio.TotalPortfolioValue
        self.peak_equity = max(self.peak_equity, equity)
        drawdown = (self.peak_equity - equity) / self.peak_equity if self.peak_equity > 0 else 0.0

        signal = self._derive_signal(data, price, drawdown)

        self._check_invariants(drawdown)

        nmode = self._next_mode(signal, drawdown)
        self._apply_mode(nmode, drawdown, price)
        self.mode = nmode

        self.prev_fast = self.fast.Current.Value
        self.prev_slow = self.slow.Current.Value

    def _derive_signal(self, data, price, drawdown) -> str:
        bar = data[self.symbol]
        if bar.Open > 0 and (bar.Close / bar.Open - 1) <= HALT_BAR_RETURN:
            return "halt"

        if self.mode in ("long", "short") and self.entry_price:
            pnl = (price / self.entry_price - 1) * (1 if self.mode == "long" else -1)
            if pnl >= TAKE_PROFIT:
                return "tp"
        f, s = self.fast.Current.Value, self.slow.Current.Value
        if self.prev_fast is None:
            return "hold"
        if self.prev_fast <= self.prev_slow and f > s:
            return "buy"
        if self.prev_fast >= self.prev_slow and f < s:
            return "sell"
        return "hold"

    def _next_mode(self, signal: str, drawdown: float) -> str:
        if self.mode == "halted":
            return "flat"
        if self.mode == "margin_warning":
            return "flat"
        if signal == "halt":
            return "halted"
        if drawdown >= DD_WARN and self.mode in ("long", "short"):
            return "margin_warning"
        if drawdown >= DD_WARN and self.mode == "flat":
            return "flat"
        if self.mode == "flat" and signal == "buy":
            return "long"
        if self.mode == "flat" and signal == "sell":
            return "short"
        if self.mode == "long" and signal in ("sell", "tp"):
            return "flat"
        if self.mode == "short" and signal in ("buy", "tp"):
            return "flat"
        return self.mode

    def _target_leverage(self, nmode: str, drawdown: float) -> float:
        if nmode in ("flat", "halted", "margin_warning"):
            return 0.0
        return float(MAX_LEVERAGE) if drawdown < 0.05 else 1.0

    def _apply_mode(self, nmode: str, drawdown: float, price: float):
        lev = self._target_leverage(nmode, drawdown)
        if nmode in ("flat", "halted", "margin_warning"):
            if self.Portfolio[self.symbol].Invested:
                self.Liquidate(self.symbol)
            self.entry_price = None
        elif nmode == "long":
            self.SetHoldings(self.symbol, lev)
            if self.entry_price is None:
                self.entry_price = price
        elif nmode == "short":
            self.SetHoldings(self.symbol, -lev)
            if self.entry_price is None:
                self.entry_price = price

    def _check_invariants(self, drawdown: float):
        holding = self.Portfolio[self.symbol]
        lev = abs(holding.HoldingsValue) / self.Portfolio.TotalPortfolioValue \
            if self.Portfolio.TotalPortfolioValue > 0 else 0.0

        if drawdown >= DD_CRIT and holding.Invested:
            self._violate("P1_no_margin_call",
                          f"drawdown={drawdown:.2%} en position -> liquidation d'urgence")
            self.Liquidate(self.symbol)

        if lev > MAX_LEVERAGE + 0.05:
            self._violate("P2_leverage_bound", f"levier reel={lev:.2f}x > {MAX_LEVERAGE}x")
            self.Liquidate(self.symbol)

    def _violate(self, invariant: str, detail: str):
        self.violations += 1
        self.Error(f"[INVARIANT CTL VIOLE] {invariant} : {detail} "
                   f"(gap modele/reel) @ {self.Time}")

    def OnEndOfAlgorithm(self):
        if self.violations == 0:
            self.Log("[MONITEUR CTL] 0 violation d'invariant : execution conforme "
                     "aux proprietes prouvees par model checking.")
        else:
            self.Log(f"[MONITEUR CTL] {self.violations} violation(s) d'invariant : "
                     "ecart modele/realite a analyser (slippage/gap/latence).")
