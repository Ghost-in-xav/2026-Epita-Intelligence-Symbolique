import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from botcheck import model_builder, pctl, properties
from botcheck.backtest import BacktestConfig, run_backtest, synthetic_prices
from botcheck.model_checker import CTLModelChecker
from botcheck.monitor import InvariantMonitor
from botcheck.strategy import BotState

def test_certified_model_satisfies_all_ctl():
    mc = CTLModelChecker(model_builder.build_kripke())
    for pid, _desc, f in properties.ctl_properties():
        assert mc.check(f).holds, f"{pid} devrait etre VRAIE sur le modele certifie"

def test_buggy_model_violates_safety():
    mc = CTLModelChecker(model_builder.build_kripke_buggy())
    res = {pid: mc.check(f) for pid, _d, f in properties.ctl_properties()}
    assert not res["P1_no_margin_call"].holds
    assert res["P1_no_margin_call"].counterexample is not None
    assert not res["P3_no_buy_in_drawdown"].holds
    assert not res["P8_crit_dd_recovers"].holds

def test_counterexample_reaches_margin_call():
    mc = CTLModelChecker(model_builder.build_kripke_buggy())
    ce = mc.check(properties.ctl_properties()[0][2]).counterexample
    last = model_builder._state(ce[-1])
    assert "margin_call" in __import__("botcheck.strategy", fromlist=["labels"]).labels(last)

def test_pctl_certified_is_certain():
    mdp = model_builder.build_mdp(p_adverse=0.3, buggy=False)
    r = pctl.prob_eventually(mdp, "margin_call", maximize=True)
    assert 1.0 - r.prob_initial >= 0.99

def test_pctl_buggy_has_risk():
    mdp = model_builder.build_mdp(p_adverse=0.3, buggy=True)
    r = pctl.prob_eventually(mdp, "margin_call", maximize=True)
    assert r.prob_initial > 0.0

def test_monitor_flags_margin_call():
    mon = InvariantMonitor()
    bad = BotState(mode="long", signal="hold", drawdown=3, leverage=2, profit=False)
    v = mon.observe(bad)
    assert any(x.invariant == "P1_no_margin_call" for x in v)
    assert not mon.clean

def test_monitor_clean_on_safe_state():
    mon = InvariantMonitor()
    mon.observe(BotState("flat", "hold", 0, 0, False))
    assert mon.clean

def test_backtest_respects_invariants():
    for seed in (1, 42, 7):
        res = run_backtest(synthetic_prices(seed=seed), BacktestConfig())
        assert res.monitor.clean, f"seed={seed}: violations {res.monitor.violations}"
        assert max(s.leverage for s in res.states) <= 2
