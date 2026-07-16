from __future__ import annotations

from typing import Iterator, List

from . import strategy
from .kripke import KripkeStructure, build_from_transition_function
from .pctl import MDP
from .strategy import BotState, DD_CRIT

def build_kripke() -> KripkeStructure:
    return build_from_transition_function(
        initial_states=[strategy.INITIAL.as_key()],
        successor_fn=lambda key: (t.as_key() for t in strategy.successors(_state(key))),
        label_fn=lambda key: strategy.labels(_state(key)),
    )

def _next_mode_buggy(s: BotState) -> str:
    if s.mode == "halted":
        return "flat"
    if s.mode == "margin_warning":
        return "flat"
    if s.signal == "halt":
        return "halted"

    if s.mode == "flat" and s.signal == "buy":
        return "long"
    if s.mode == "flat" and s.signal == "sell":
        return "short"
    if s.mode == "long" and s.signal in ("sell", "tp"):
        return "flat"
    if s.mode == "short" and s.signal in ("buy", "tp"):
        return "flat"
    return s.mode

def _next_leverage_buggy(s: BotState, nmode: str) -> int:
    if nmode in ("flat", "halted", "margin_warning"):
        return 0
    return strategy.MAX_LEVERAGE

def _successors_buggy(s: BotState) -> Iterator[BotState]:
    nmode = _next_mode_buggy(s)
    nlev = _next_leverage_buggy(s, nmode)
    nprofit = strategy.next_profit(s)
    for ndd in strategy.drawdown_dynamics(s):
        for nsig in strategy.SIGNALS:
            yield BotState(mode=nmode, signal=nsig, drawdown=ndd,
                           leverage=nlev, profit=nprofit)

def build_kripke_buggy() -> KripkeStructure:
    return build_from_transition_function(
        initial_states=[strategy.INITIAL.as_key()],
        successor_fn=lambda key: (t.as_key() for t in _successors_buggy(_state(key))),
        label_fn=lambda key: strategy.labels(_state(key)),
    )

def build_mdp(p_adverse: float = 0.30, buggy: bool = False) -> MDP:
    mdp = MDP()
    init = strategy.INITIAL.as_key()
    mdp.set_initial(init)
    frontier: List = [init]
    seen = {init}
    n_sig = len(strategy.SIGNALS)

    nmode_fn = _next_mode_buggy if buggy else strategy.next_mode
    nlev_fn = _next_leverage_buggy if buggy else strategy.next_leverage

    while frontier:
        key = frontier.pop()
        s = _state(key)
        mdp.set_labels(key, strategy.labels(s))
        nmode = nmode_fn(s)
        nlev = nlev_fn(s, nmode)
        nprofit = strategy.next_profit(s)

        if s.leverage > 0:
            worse = min(DD_CRIT, s.drawdown + 1)
            if worse == s.drawdown:
                dd_dist = {s.drawdown: 1.0}
            else:
                dd_dist = {worse: p_adverse, s.drawdown: 1.0 - p_adverse}
        else:
            dd_dist = {max(0, s.drawdown - 1): 1.0}

        dist = {}
        for ndd, pdd in dd_dist.items():
            for nsig in strategy.SIGNALS:
                t = BotState(mode=nmode, signal=nsig, drawdown=ndd,
                             leverage=nlev, profit=nprofit).as_key()
                dist[t] = dist.get(t, 0.0) + pdd / n_sig
                if t not in seen:
                    seen.add(t)
                    frontier.append(t)
        mdp.add_action(key, "step", dist)

    return mdp

def _state(key) -> BotState:
    mode, signal, drawdown, leverage, profit = key
    return BotState(mode=mode, signal=signal, drawdown=drawdown,
                    leverage=leverage, profit=profit)
