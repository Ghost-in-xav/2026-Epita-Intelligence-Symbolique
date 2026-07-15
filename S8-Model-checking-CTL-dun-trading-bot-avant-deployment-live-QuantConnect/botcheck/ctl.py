from __future__ import annotations

from dataclasses import dataclass
from typing import Union

class Formula:
    def __and__(self, other: "Formula") -> "And":
        return And(self, other)

    def __or__(self, other: "Formula") -> "Or":
        return Or(self, other)

    def __invert__(self) -> "Not":
        return Not(self)

@dataclass(frozen=True)
class Bool(Formula):
    value: bool

    def __str__(self) -> str:
        return "true" if self.value else "false"

@dataclass(frozen=True)
class Atom(Formula):
    name: str

    def __str__(self) -> str:
        return self.name

@dataclass(frozen=True)
class Not(Formula):
    arg: Formula

    def __str__(self) -> str:
        return f"!{_paren(self.arg)}"

@dataclass(frozen=True)
class And(Formula):
    left: Formula
    right: Formula

    def __str__(self) -> str:
        return f"({self.left} & {self.right})"

@dataclass(frozen=True)
class Or(Formula):
    left: Formula
    right: Formula

    def __str__(self) -> str:
        return f"({self.left} | {self.right})"

@dataclass(frozen=True)
class Implies(Formula):
    left: Formula
    right: Formula

    def __str__(self) -> str:
        return f"({self.left} -> {self.right})"

@dataclass(frozen=True)
class EX(Formula):
    arg: Formula

    def __str__(self) -> str:
        return f"EX {_paren(self.arg)}"

@dataclass(frozen=True)
class EU(Formula):
    left: Formula
    right: Formula

    def __str__(self) -> str:
        return f"E[{self.left} U {self.right}]"

@dataclass(frozen=True)
class EG(Formula):
    arg: Formula

    def __str__(self) -> str:
        return f"EG {_paren(self.arg)}"

@dataclass(frozen=True)
class EF(Formula):
    arg: Formula

    def __str__(self) -> str:
        return f"EF {_paren(self.arg)}"

@dataclass(frozen=True)
class AX(Formula):
    arg: Formula

    def __str__(self) -> str:
        return f"AX {_paren(self.arg)}"

@dataclass(frozen=True)
class AF(Formula):
    arg: Formula

    def __str__(self) -> str:
        return f"AF {_paren(self.arg)}"

@dataclass(frozen=True)
class AG(Formula):
    arg: Formula

    def __str__(self) -> str:
        return f"AG {_paren(self.arg)}"

@dataclass(frozen=True)
class AU(Formula):
    left: Formula
    right: Formula

    def __str__(self) -> str:
        return f"A[{self.left} U {self.right}]"

def _paren(f: Formula) -> str:
    if isinstance(f, (Atom, Bool, Not, EX, EF, EG, AX, AF, AG)):
        return str(f)
    return f"({f})"

TRUE = Bool(True)
FALSE = Bool(False)

def atom(name: str) -> Atom:
    return Atom(name)

def implies(p: Formula, q: Formula) -> Implies:
    return Implies(p, q)

FormulaLike = Union[Formula, str, bool]

def lift(x: FormulaLike) -> Formula:
    if isinstance(x, Formula):
        return x
    if isinstance(x, bool):
        return Bool(x)
    if isinstance(x, str):
        return Atom(x)
    raise TypeError(f"Impossible de convertir {x!r} en Formula")
