"""Baselines de comparaison : LLM seul, CSP seul."""

from __future__ import annotations

from .generator import Generator, parse_plan
from .loop import Cycle, LoopOutcome
from .schema import Syllabus
from .validator import Validator


async def llm_only(syllabus: Syllabus, generator: Generator) -> LoopOutcome:
    """Une passe, aucun feedback symbolique."""
    validator = Validator(syllabus)
    try:
        raw = await generator.generate(syllabus_json=syllabus.to_prompt_json(), feedback="")
        plan = parse_plan(raw)
    except Exception as exc:
        return LoopOutcome(False, None, [Cycle(0, None, None, "", error=str(exc))])

    result = validator.validate(plan)
    return LoopOutcome(result.is_valid, plan, [Cycle(0, plan, result, "")])


def csp_only(syllabus: Syllabus) -> LoopOutcome:
    """CP-SAT seul : valide par construction, titres generiques."""
    validator = Validator(syllabus)
    plan = validator.solve()
    if plan is None:
        return LoopOutcome(False, None)

    result = validator.validate(plan)
    # Un desaccord entre solve et validate signifie que l'un des deux encode mal le domaine.
    assert result.is_valid, f"Incoherence solve/validate : {result.summary()}"
    return LoopOutcome(True, plan, [Cycle(0, plan, result, "")])
