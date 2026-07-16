"""Problem specification.

A problem couples a natural-language statement (what the LLM reads) with a
formal Z3 ground truth (what the verifier checks). The LLM never sees the Z3
model; it must *reason* to a candidate assignment, which the symbolic verifier
then accepts or rejects. This is the LLM-as-a-reasoner / symbolic-verifier split
at the heart of subject M1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import z3

# A builder returns the decision variables (by name) and the ground-truth
# constraints over them. It must create fresh Z3 objects on each call.
Builder = Callable[[], tuple[dict[str, z3.ExprRef], list[z3.BoolRef]]]


@dataclass
class Problem:
    id: str
    title: str
    domain: str
    statement: str          # natural-language prompt shown to the LLM
    answer_format: str      # human description of the expected JSON keys/domains
    builder: Builder        # Z3 ground truth
    satisfiable: bool = True
    few_shot: str | None = None  # optional worked example for the few-shot baseline
    tags: list[str] = field(default_factory=list)

    def variable_names(self) -> list[str]:
        variables, _ = self.builder()
        return list(variables.keys())

    def expected_keys_doc(self) -> str:
        return self.answer_format
