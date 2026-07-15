import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from botcheck import ctl
from botcheck.kripke import KripkeStructure
from botcheck.model_checker import CTLModelChecker

def tiny():
    ks = KripkeStructure()
    ks.add_state("s0", ["a"], initial=True)
    ks.add_state("s1", ["a", "b"])
    ks.add_state("s2", ["c"])
    ks.add_transition("s0", "s1")
    ks.add_transition("s1", "s0")
    ks.add_transition("s1", "s2")
    ks.add_transition("s2", "s2")
    return ks

def test_ef_reachable():
    mc = CTLModelChecker(tiny())
    assert mc.check(ctl.EF(ctl.Atom("c"))).holds

def test_ag_violation_has_counterexample():
    mc = CTLModelChecker(tiny())
    r = mc.check(ctl.AG(ctl.Atom("a")))
    assert not r.holds
    assert r.counterexample is not None
    assert r.counterexample[0] == "s0"
    assert "a" not in tiny().labels[r.counterexample[-1]]

def test_af_false_on_cycle():
    mc = CTLModelChecker(tiny())
    assert not mc.check(ctl.AF(ctl.Atom("c"))).holds

def test_eg_true_on_cycle():
    mc = CTLModelChecker(tiny())
    assert mc.check(ctl.EG(ctl.Atom("a"))).holds

def test_ax():
    mc = CTLModelChecker(tiny())
    assert mc.check(ctl.AX(ctl.Atom("a"))).holds

def test_implies_and_nesting():
    mc = CTLModelChecker(tiny())
    f = ctl.AG(ctl.Implies(ctl.Atom("b"), ctl.EF(ctl.Atom("c"))))
    assert mc.check(f).holds

def test_totality_enforced():
    ks = KripkeStructure()
    ks.add_state("dead", [], initial=True)
    try:
        CTLModelChecker(ks)
        assert False, "doit lever une erreur de non-totalite"
    except ValueError:
        pass
