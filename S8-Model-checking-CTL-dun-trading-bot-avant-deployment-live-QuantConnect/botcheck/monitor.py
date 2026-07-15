from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .strategy import (DD_CRIT, DD_WARN, MAX_LEVERAGE, BotState, labels)

@dataclass
class Violation:
    bar: int
    invariant: str
    state: BotState
    detail: str = ""

    def __str__(self) -> str:
        d = f" ({self.detail})" if self.detail else ""
        return f"barre {self.bar}: VIOLATION [{self.invariant}] en {self.state}{d}"

@dataclass
class ModelGap:
    bar: int
    kind: str
    state: BotState
    detail: str = ""

    def __str__(self) -> str:
        d = f" ({self.detail})" if self.detail else ""
        return f"barre {self.bar}: GAP MODELE/REEL [{self.kind}] en {self.state}{d}"

SAFETY_INVARIANTS: Dict[str, Callable[[BotState], bool]] = {

    "P1_no_margin_call": lambda s: not (s.drawdown >= DD_CRIT and s.leverage > 0),

    "P2_leverage_bound": lambda s: s.leverage <= MAX_LEVERAGE,
}

@dataclass
class InvariantMonitor:
    halt_recovery_budget: int = 3
    warning_recovery_budget: int = 2

    violations: List[Violation] = field(default_factory=list)
    gaps: List["ModelGap"] = field(default_factory=list)
    _bar: int = 0
    _halt_countdown: Optional[int] = None
    _warn_countdown: Optional[int] = None
    history: List[BotState] = field(default_factory=list)

    def observe(self, s: BotState) -> List[Violation]:
        found: List[Violation] = []
        prev = self.history[-1] if self.history else None

        for name, pred in SAFETY_INVARIANTS.items():
            if not pred(s):
                v = Violation(self._bar, name, s)
                found.append(v)

        if (prev is not None and prev.mode == "flat" and prev.drawdown >= DD_WARN
                and s.mode in ("long", "short")):
            found.append(Violation(self._bar, "P3_no_buy_in_drawdown", s,
                                   "ouverture de position sous drawdown d'alerte"))

        if prev is not None and abs(s.drawdown - prev.drawdown) >= 2:
            self.gaps.append(ModelGap(self._bar, "drawdown_jump", s,
                                      f"{prev.drawdown} -> {s.drawdown} en une barre"))

        if self._halt_countdown is not None:
            if s.mode == "flat":
                self._halt_countdown = None
            else:
                self._halt_countdown -= 1
                if self._halt_countdown < 0:
                    found.append(Violation(self._bar, "P4_halt_flattens", s,
                                           "non revenu a flat dans le budget"))
                    self._halt_countdown = None
        if s.mode == "halted":
            self._halt_countdown = self.halt_recovery_budget

        if self._warn_countdown is not None:
            if s.mode == "flat":
                self._warn_countdown = None
            else:
                self._warn_countdown -= 1
                if self._warn_countdown < 0:
                    found.append(Violation(self._bar, "P5_warning_flattens", s,
                                           "non revenu a flat dans le budget"))
                    self._warn_countdown = None
        if s.mode == "margin_warning":
            self._warn_countdown = self.warning_recovery_budget

        self.history.append(s)
        self.violations.extend(found)
        self._bar += 1
        return found

    @property
    def clean(self) -> bool:
        return not self.violations

    def report(self) -> str:
        gap_note = ""
        if self.gaps:
            gap_note = (f"\n[GAP MODELE/REEL] {len(self.gaps)} ecart(s) detecte(s) "
                        f"(sauts de drawdown > 1 bucket ; hypothese du modele depassee).")
        if self.clean:
            return (f"[MONITEUR] {self._bar} barres observees, "
                    f"0 violation d'invariant CTL. Comportement conforme a la preuve."
                    + gap_note)
        lines = [f"[MONITEUR] {len(self.violations)} violation(s) sur {self._bar} barres :"]
        lines += [f"  - {v}" for v in self.violations]
        return "\n".join(lines) + gap_note
