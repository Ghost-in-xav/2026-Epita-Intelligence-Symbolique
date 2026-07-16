from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, Hashable, List, Set, Tuple

PState = Hashable
Distribution = Dict[PState, float]

@dataclass
class MDP:
    states: Set[PState] = field(default_factory=set)
    initial: PState = None

    actions: Dict[PState, List[Tuple[str, Distribution]]] = field(default_factory=dict)
    labels: Dict[PState, FrozenSet[str]] = field(default_factory=dict)

    def set_initial(self, s: PState) -> None:
        self.initial = s
        self.states.add(s)
        self.actions.setdefault(s, [])

    def add_action(self, s: PState, name: str, dist: Distribution) -> None:
        total = sum(dist.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"Distribution non normalisee en {s!r} (somme={total})")
        self.states.add(s)
        self.actions.setdefault(s, []).append((name, dict(dist)))
        for t in dist:
            self.states.add(t)
            self.actions.setdefault(t, [])

    def set_labels(self, s: PState, props) -> None:
        self.labels[s] = frozenset(props)

    def sat(self, ap: str) -> Set[PState]:
        return {s for s in self.states if ap in self.labels.get(s, frozenset())}

    def __str__(self) -> str:
        n_act = sum(len(v) for v in self.actions.values())
        return f"MDP(|S|={len(self.states)}, |Act|={n_act})"

def _reach_prob(
    mdp: MDP,
    target: Set[PState],
    maximize: bool,
    epsilon: float = 1e-9,
    max_iter: int = 100_000,
) -> Dict[PState, float]:
    x: Dict[PState, float] = {s: (1.0 if s in target else 0.0) for s in mdp.states}
    opt = max if maximize else min
    for _ in range(max_iter):
        delta = 0.0
        new_x = dict(x)
        for s in mdp.states:
            if s in target:
                continue
            acts = mdp.actions.get(s, [])
            if not acts:
                continue
            vals = []
            for _name, dist in acts:
                vals.append(sum(p * x[t] for t, p in dist.items()))
            val = opt(vals)
            new_x[s] = val
            delta = max(delta, abs(val - x[s]))
        x = new_x
        if delta < epsilon:
            break
    return x

@dataclass
class PCTLResult:
    query: str
    prob_initial: float
    holds: bool = None
    threshold: float = None
    op: str = None

    def __str__(self) -> str:
        s = f"{self.query} = {self.prob_initial:.6f}"
        if self.holds is not None:
            verdict = "OK" if self.holds else "ECHEC"
            s += f"   [{verdict}] (seuil {self.op} {self.threshold})"
        return s

def prob_eventually(mdp: MDP, target_ap: str, maximize: bool = True) -> PCTLResult:
    target = mdp.sat(target_ap)
    x = _reach_prob(mdp, target, maximize=maximize)
    q = f"P{'max' if maximize else 'min'}=? [ F {target_ap} ]"
    return PCTLResult(query=q, prob_initial=x[mdp.initial])

def prob_globally(mdp: MDP, safe_ap: str, maximize: bool = True) -> PCTLResult:
    unsafe = mdp.states - mdp.sat(safe_ap)

    x = _reach_prob(mdp, unsafe, maximize=not maximize)
    prob = 1.0 - x[mdp.initial]
    q = f"P{'max' if maximize else 'min'}=? [ G {safe_ap} ]"
    return PCTLResult(query=q, prob_initial=prob)

def check_threshold(result: PCTLResult, op: str, threshold: float) -> PCTLResult:
    p = result.prob_initial
    holds = {
        ">=": p >= threshold - 1e-9,
        ">": p > threshold + 1e-9,
        "<=": p <= threshold + 1e-9,
        "<": p < threshold - 1e-9,
    }[op]
    result.holds = holds
    result.op = op
    result.threshold = threshold
    return result
