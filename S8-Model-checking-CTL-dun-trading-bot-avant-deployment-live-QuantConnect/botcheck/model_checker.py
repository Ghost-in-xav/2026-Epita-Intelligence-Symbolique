from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from . import ctl
from .ctl import Formula
from .kripke import KripkeStructure, State

@dataclass
class CheckResult:
    formula: Formula
    holds: bool
    sat: Set[State]
    counterexample: Optional[List[State]] = None
    witness: Optional[List[State]] = None

    def __str__(self) -> str:
        status = "OK " if self.holds else "ECHEC"
        return f"[{status}] {self.formula}"

class CTLModelChecker:
    def __init__(self, ks: KripkeStructure):
        ks.assert_total()
        self.ks = ks
        self._pred = ks.predecessors_map()
        self._sat_cache: Dict[Formula, Set[State]] = {}

    def sat(self, phi: Formula) -> Set[State]:
        if phi in self._sat_cache:
            return self._sat_cache[phi]
        result = self._sat(phi)
        self._sat_cache[phi] = result
        return result

    def _sat(self, phi: Formula) -> Set[State]:
        S = self.ks.states

        if isinstance(phi, ctl.Bool):
            return set(S) if phi.value else set()

        if isinstance(phi, ctl.Atom):
            return {s for s in S if phi.name in self.ks.labels[s]}

        if isinstance(phi, ctl.Not):
            return S - self.sat(phi.arg)

        if isinstance(phi, ctl.And):
            return self.sat(phi.left) & self.sat(phi.right)

        if isinstance(phi, ctl.Or):
            return self.sat(phi.left) | self.sat(phi.right)

        if isinstance(phi, ctl.Implies):
            return (S - self.sat(phi.left)) | self.sat(phi.right)

        if isinstance(phi, ctl.EX):
            return self._pre_exists(self.sat(phi.arg))

        if isinstance(phi, ctl.EU):
            return self._sat_EU(self.sat(phi.left), self.sat(phi.right))

        if isinstance(phi, ctl.EG):
            return self._sat_EG(self.sat(phi.arg))

        if isinstance(phi, ctl.EF):
            return self._sat_EU(set(S), self.sat(phi.arg))

        if isinstance(phi, ctl.AX):
            return S - self._pre_exists(S - self.sat(phi.arg))

        if isinstance(phi, ctl.AF):
            return S - self._sat_EG(S - self.sat(phi.arg))

        if isinstance(phi, ctl.AG):
            return S - self._sat_EU(set(S), S - self.sat(phi.arg))

        if isinstance(phi, ctl.AU):
            sp, sq = self.sat(phi.left), self.sat(phi.right)
            not_p, not_q = S - sp, S - sq
            e_until = self._sat_EU(not_q, not_p & not_q)
            eg_notq = self._sat_EG(not_q)
            return (S - e_until) & (S - eg_notq)

        raise TypeError(f"Formule CTL non reconnue : {type(phi).__name__}")

    def _pre_exists(self, target: Set[State]) -> Set[State]:
        result: Set[State] = set()
        for t in target:
            result.update(self._pred.get(t, ()))
        return result

    def _sat_EU(self, sp: Set[State], sq: Set[State]) -> Set[State]:
        result = set(sq)
        worklist = deque(sq)
        while worklist:
            t = worklist.popleft()
            for s in self._pred.get(t, ()):
                if s not in result and s in sp:
                    result.add(s)
                    worklist.append(s)
        return result

    def _sat_EG(self, sp: Set[State]) -> Set[State]:
        result = set(sp)
        changed = True
        while changed:
            changed = False
            to_remove = set()
            for s in result:
                if not any(t in result for t in self.ks.successors.get(s, ())):
                    to_remove.add(s)
            if to_remove:
                result -= to_remove
                changed = True
        return result

    def check(self, phi: Formula) -> CheckResult:
        sat = self.sat(phi)
        holds = self.ks.initial.issubset(sat)
        ce = None
        wit = None
        if not holds:
            ce = self._counterexample(phi, sat)
        else:
            wit = self._witness(phi, sat)
        return CheckResult(formula=phi, holds=holds, sat=sat,
                           counterexample=ce, witness=wit)

    def _bad_initial(self, sat: Set[State]) -> Optional[State]:
        for s in self.ks.initial:
            if s not in sat:
                return s
        return None

    def _counterexample(self, phi: Formula, sat: Set[State]) -> Optional[List[State]]:
        start = self._bad_initial(sat)
        if start is None:
            return None

        if isinstance(phi, ctl.AG):
            bad = self.sat(ctl.Not(phi.arg))
            path = self._bfs_path(self.ks.initial, bad)
            return path or [start]

        if isinstance(phi, ctl.AF):
            eg_notp = self._sat_EG(self.ks.states - self.sat(phi.arg))
            lasso = self._lasso_in(self.ks.initial, eg_notp)
            return lasso or [start]

        if isinstance(phi, (ctl.AX,)):
            for t in self.ks.successors.get(start, ()):
                if t not in self.sat(phi.arg):
                    return [start, t]
            return [start]

        return [start]

    def _witness(self, phi: Formula, sat: Set[State]) -> Optional[List[State]]:
        if isinstance(phi, ctl.EF):
            target = self.sat(phi.arg)
            return self._bfs_path(self.ks.initial, target)
        if isinstance(phi, ctl.EU):
            target = self.sat(phi.right)
            return self._bfs_path(self.ks.initial, target)
        return None

    def _bfs_path(self, sources: Set[State], targets: Set[State]) -> Optional[List[State]]:
        if not targets:
            return None
        prev: Dict[State, Optional[State]] = {}
        q: deque[State] = deque()
        for s in sources:
            prev[s] = None
            q.append(s)
            if s in targets:
                return [s]
        while q:
            s = q.popleft()
            for t in self.ks.successors.get(s, ()):
                if t not in prev:
                    prev[t] = s
                    if t in targets:
                        return self._reconstruct(prev, t)
                    q.append(t)
        return None

    def _lasso_in(self, sources: Set[State], region: Set[State]) -> Optional[List[State]]:
        entry_path = self._bfs_path(sources, region)
        if not entry_path:
            return None

        path = list(entry_path)
        seen = {s: i for i, s in enumerate(path)}
        cur = path[-1]
        while True:
            nxt = next((t for t in self.ks.successors.get(cur, ()) if t in region), None)
            if nxt is None:
                return path
            if nxt in seen:
                path.append(nxt)
                return path
            seen[nxt] = len(path)
            path.append(nxt)
            cur = nxt

    @staticmethod
    def _reconstruct(prev: Dict[State, Optional[State]], end: State) -> List[State]:
        path: List[State] = []
        cur: Optional[State] = end
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        return path
