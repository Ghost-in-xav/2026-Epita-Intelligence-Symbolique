"""Symbolic verifier.

Given a candidate assignment (parsed from the LLM output), the verifier checks it
against the problem's Z3 ground truth. Verification is rigorous: every constraint
is instantiated with the candidate values and simplified to ``True``/``False``.
Rejected assignments come back with the exact list of violated constraints, which
the counterexample-guided strategy feeds back to the LLM.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import z3

from .problems.base import Problem


class Status(str, Enum):
    ACCEPTED = "accepted"               # satisfies every constraint
    CONSTRAINT_VIOLATION = "constraint_violation"  # well-formed but wrong
    SCHEMA_ERROR = "schema_error"       # missing/extra keys or wrong value type
    PARSE_ERROR = "parse_error"         # no JSON object could be extracted


@dataclass
class VerificationResult:
    status: Status
    violated: list[str] = field(default_factory=list)
    message: str = ""
    assignment: dict | None = None

    @property
    def ok(self) -> bool:
        return self.status is Status.ACCEPTED

    @property
    def error_category(self) -> str:
        return self.status.value


def to_z3_value(var: z3.ExprRef, value) -> z3.ExprRef:
    """Convert a JSON scalar to a Z3 literal matching ``var``'s sort."""
    sort = var.sort()
    if sort == z3.IntSort():
        # bool is a subclass of int in Python; reject it for integer vars.
        if isinstance(value, bool):
            raise TypeError(f"{var} expects an integer, got boolean {value!r}")
        if isinstance(value, int):
            return z3.IntVal(value)
        if isinstance(value, str) and value.strip().lstrip("-").isdigit():
            return z3.IntVal(int(value))
        raise TypeError(f"{var} expects an integer, got {value!r}")
    if sort == z3.BoolSort():
        if isinstance(value, bool):
            return z3.BoolVal(value)
        if isinstance(value, str) and value.strip().lower() in ("true", "false"):
            return z3.BoolVal(value.strip().lower() == "true")
        raise TypeError(f"{var} expects a boolean, got {value!r}")
    raise TypeError(f"unsupported sort {sort} for {var}")


def verify(problem: Problem, solution: dict | None) -> VerificationResult:
    """Check ``solution`` against the problem's Z3 ground truth."""
    if solution is None:
        return VerificationResult(
            status=Status.PARSE_ERROR,
            message="no JSON object could be parsed from the model output",
        )

    variables, constraints = problem.builder()

    missing = [n for n in variables if n not in solution]
    extra = [k for k in solution if k not in variables]
    if missing or extra:
        bits = []
        if missing:
            bits.append(f"missing keys: {missing}")
        if extra:
            bits.append(f"unexpected keys: {extra}")
        return VerificationResult(
            status=Status.SCHEMA_ERROR,
            message="; ".join(bits),
            assignment=solution,
        )

    subs: list[tuple[z3.ExprRef, z3.ExprRef]] = []
    for name, var in variables.items():
        try:
            subs.append((var, to_z3_value(var, solution[name])))
        except TypeError as exc:
            return VerificationResult(
                status=Status.SCHEMA_ERROR,
                message=str(exc),
                assignment=solution,
            )

    violated: list[str] = []
    for c in constraints:
        grounded = z3.simplify(z3.substitute(c, *subs))
        if not z3.is_true(grounded):
            violated.append(str(c))

    if violated:
        return VerificationResult(
            status=Status.CONSTRAINT_VIOLATION,
            violated=violated,
            message=f"{len(violated)} constraint(s) violated",
            assignment=solution,
        )

    return VerificationResult(status=Status.ACCEPTED, assignment=solution)


def solve(problem: Problem) -> dict | None:
    """Return one satisfying assignment via Z3, or ``None`` if UNSAT.

    This is the symbolic *solver-only* baseline / oracle.
    """
    variables, constraints = problem.builder()
    s = z3.Solver()
    for c in constraints:
        s.add(c)
    if s.check() != z3.sat:
        return None
    model = s.model()
    out: dict = {}
    for name, var in variables.items():
        val = model.eval(var, model_completion=True)
        out[name] = bool(z3.is_true(val)) if var.sort() == z3.BoolSort() else val.as_long()
    return out
