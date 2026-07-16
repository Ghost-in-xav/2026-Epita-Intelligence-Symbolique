from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, Hashable, Iterable, List, Set, Tuple

State = Hashable

@dataclass
class KripkeStructure:
    states: Set[State] = field(default_factory=set)
    initial: Set[State] = field(default_factory=set)
    successors: Dict[State, Set[State]] = field(default_factory=dict)
    labels: Dict[State, FrozenSet[str]] = field(default_factory=dict)
    atoms: Set[str] = field(default_factory=set)

    def add_state(self, s: State, props: Iterable[str] = (), initial: bool = False) -> None:
        self.states.add(s)
        self.successors.setdefault(s, set())
        labelset = frozenset(props)
        self.labels[s] = labelset
        self.atoms.update(labelset)
        if initial:
            self.initial.add(s)

    def add_transition(self, src: State, dst: State) -> None:
        self.successors.setdefault(src, set()).add(dst)
        self.successors.setdefault(dst, set())

    def predecessors_map(self) -> Dict[State, Set[State]]:
        pred: Dict[State, Set[State]] = {s: set() for s in self.states}
        for s, succ in self.successors.items():
            for t in succ:
                pred.setdefault(t, set()).add(s)
        return pred

    def assert_total(self) -> None:
        dead = [s for s in self.states if not self.successors.get(s)]
        if dead:
            raise ValueError(
                f"Relation de transition non totale : {len(dead)} etat(s) sans "
                f"successeur, p.ex. {dead[0]!r}. Ajoutez un self-loop."
            )

    def reachable_states(self) -> Set[State]:
        seen: Set[State] = set(self.initial)
        stack: List[State] = list(self.initial)
        while stack:
            s = stack.pop()
            for t in self.successors.get(s, ()):
                if t not in seen:
                    seen.add(t)
                    stack.append(t)
        return seen

    def __str__(self) -> str:
        n_trans = sum(len(v) for v in self.successors.values())
        return (
            f"KripkeStructure(|S|={len(self.states)}, |I|={len(self.initial)}, "
            f"|R|={n_trans}, |AP|={len(self.atoms)})"
        )

def build_from_transition_function(
    initial_states: Iterable[State],
    successor_fn: Callable[[State], Iterable[State]],
    label_fn: Callable[[State], Iterable[str]],
) -> KripkeStructure:
    ks = KripkeStructure()
    frontier: List[State] = []
    for s in initial_states:
        if s not in ks.states:
            ks.add_state(s, label_fn(s), initial=True)
            frontier.append(s)
    while frontier:
        s = frontier.pop()
        for t in successor_fn(s):
            if t not in ks.states:
                ks.add_state(t, label_fn(t))
                frontier.append(t)
            ks.add_transition(s, t)
    return ks
