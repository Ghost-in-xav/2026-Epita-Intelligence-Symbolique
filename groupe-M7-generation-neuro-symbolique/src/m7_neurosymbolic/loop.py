"""Boucle neuro-symbolique : generer, valider, expliquer, regenerer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .feedback import build_feedback
from .generator import Generator, parse_plan
from .schema import PlanCandidate, Syllabus, ValidationResult
from .validator import Validator


@dataclass
class Cycle:
    index: int
    plan: PlanCandidate | None
    result: ValidationResult | None
    feedback: str
    error: str | None = None

    @property
    def n_violations(self) -> int:
        return len(self.result.violations) if self.result else -1


@dataclass
class LoopOutcome:
    converged: bool
    final_plan: PlanCandidate | None
    cycles: list[Cycle] = field(default_factory=list)
    infeasible_reasons: list[str] = field(default_factory=list)

    @property
    def n_cycles(self) -> int:
        return len(self.cycles)

    @property
    def violation_trajectory(self) -> list[int]:
        return [c.n_violations for c in self.cycles]


async def run_loop(
    syllabus: Syllabus,
    generator: Generator,
    max_cycles: int = 5,
    feedback_builder: Callable[[ValidationResult], str] = build_feedback,
) -> LoopOutcome:
    """Boucle jusqu'a validite ou epuisement du budget.

    feedback_builder est injecte pour comparer feedback cible et feedback naif sans dupliquer
    la boucle.
    """
    validator = Validator(syllabus)

    feasible, reasons = validator.is_instance_feasible()
    if not feasible:
        return LoopOutcome(converged=False, final_plan=None, infeasible_reasons=reasons)

    syllabus_json = syllabus.to_prompt_json()
    cycles: list[Cycle] = []
    feedback = ""

    for index in range(max_cycles):
        try:
            raw = await generator.generate(syllabus_json=syllabus_json, feedback=feedback)
            plan = parse_plan(raw)
        except Exception as exc:
            # JSON casse ou appel echoue : on compte l'incident, le taux de sorties
            # malformees fait partie des resultats.
            cycles.append(Cycle(index, None, None, feedback, error=str(exc)))
            feedback = "Ta reponse n'etait pas un JSON valide. Renvoie uniquement l'objet JSON."
            continue

        result = validator.validate(plan)
        cycles.append(Cycle(index, plan, result, feedback))

        if result.is_valid:
            return LoopOutcome(converged=True, final_plan=plan, cycles=cycles)

        feedback = feedback_builder(result)

    last_plan = next((c.plan for c in reversed(cycles) if c.plan is not None), None)
    return LoopOutcome(converged=False, final_plan=last_plan, cycles=cycles)
