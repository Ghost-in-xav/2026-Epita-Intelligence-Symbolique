from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, List, Tuple

MODES = ("flat", "long", "short", "margin_warning", "halted")
SIGNALS = ("buy", "sell", "hold", "halt", "tp")
DD_LEVELS = (0, 1, 2, 3)
LEV_LEVELS = (0, 1, 2)
MAX_LEVERAGE = 2

DD_WARN = 2
DD_CRIT = 3

@dataclass(frozen=True)
class BotState:
    mode: str
    signal: str
    drawdown: int
    leverage: int
    profit: bool

    def as_key(self) -> Tuple:
        return (self.mode, self.signal, self.drawdown, self.leverage, self.profit)

    def __str__(self) -> str:
        return (f"{self.mode}|sig={self.signal}|dd={self.drawdown}"
                f"|lev={self.leverage}|profit={int(self.profit)}")

INITIAL = BotState(mode="flat", signal="hold", drawdown=0, leverage=0, profit=False)

def next_mode(s: BotState) -> str:
    if s.mode == "halted":
        return "flat"
    if s.mode == "margin_warning":
        return "flat"

    if s.signal == "halt":
        return "halted"

    if s.drawdown >= DD_WARN and s.mode in ("long", "short"):
        return "margin_warning"

    if s.drawdown >= DD_WARN and s.mode == "flat":
        return "flat"

    if s.mode == "flat" and s.signal == "buy":
        return "long"
    if s.mode == "flat" and s.signal == "sell":
        return "short"
    if s.mode == "long" and s.signal in ("sell", "tp"):
        return "flat"
    if s.mode == "short" and s.signal in ("buy", "tp"):
        return "flat"

    return s.mode

def next_leverage(s: BotState, nmode: str) -> int:
    if nmode in ("flat", "halted", "margin_warning"):
        return 0

    if s.drawdown < 1:
        return MAX_LEVERAGE
    return 1

def next_profit(s: BotState) -> bool:
    if s.profit:
        return True
    return s.signal == "tp" and s.mode in ("long", "short")

def drawdown_dynamics(s: BotState) -> List[int]:
    if s.leverage > 0:
        worse = min(DD_CRIT, s.drawdown + 1)
        return sorted({s.drawdown, worse})
    return [max(0, s.drawdown - 1)]

def successors(s: BotState) -> Iterator[BotState]:
    nmode = next_mode(s)
    nlev = next_leverage(s, nmode)
    nprofit = next_profit(s)
    for ndd in drawdown_dynamics(s):
        for nsig in SIGNALS:
            yield BotState(mode=nmode, signal=nsig, drawdown=ndd,
                           leverage=nlev, profit=nprofit)

def labels(s: BotState) -> List[str]:
    aps: List[str] = []

    aps.append(s.mode)
    if s.mode in ("long", "short"):
        aps.append("in_position")

    aps.append(f"sig_{s.signal}")

    if s.drawdown >= DD_WARN:
        aps.append("dd_warn")
    if s.drawdown >= DD_CRIT:
        aps.append("dd_crit")

    if s.leverage > MAX_LEVERAGE:
        aps.append("leverage_breach")

    if s.drawdown >= DD_CRIT and s.leverage > 0:
        aps.append("margin_call")

    if s.mode == "flat" and s.drawdown < DD_WARN and s.signal in ("buy", "sell"):
        aps.append("opening")
    if s.profit:
        aps.append("profit_target")
    return aps
