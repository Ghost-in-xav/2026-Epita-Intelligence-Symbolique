"""Tests de la boucle, avec un generateur scripte (ni reseau ni cle API)."""

from __future__ import annotations

import json

import pytest

from m7_neurosymbolic.baselines import csp_only, llm_only
from m7_neurosymbolic.feedback import build_feedback, build_naive_feedback
from m7_neurosymbolic.generator import ScriptedGenerator
from m7_neurosymbolic.loop import run_loop
from m7_neurosymbolic.schema import LearningObjective, Syllabus


@pytest.fixture
def syllabus() -> Syllabus:
    return Syllabus(
        objectives=(
            LearningObjective("A", "Bases"),
            LearningObjective("B", "Avance", ("A",)),
        ),
        n_sessions=2,
        min_duration=1,
        max_duration=2,
    )


def response(*sessions: dict) -> str:
    return json.dumps({"sessions": list(sessions)})


VALID = response(
    {"title": "Bases", "objectives": ["A"], "start_slot": 0, "duration": 1},
    {"title": "Avance", "objectives": ["B"], "start_slot": 1, "duration": 1},
)

BAD_ORDER = response(
    {"title": "Avance", "objectives": ["B"], "start_slot": 0, "duration": 1},
    {"title": "Bases", "objectives": ["A"], "start_slot": 1, "duration": 1},
)


async def test_loop_converges_immediately_on_valid_plan(syllabus: Syllabus) -> None:
    outcome = await run_loop(syllabus, ScriptedGenerator([VALID]))
    assert outcome.converged
    assert outcome.n_cycles == 1


async def test_loop_recovers_after_bad_plan(syllabus: Syllabus) -> None:
    """Premier plan invalide, second correct : la boucle doit converger en 2 cycles."""
    outcome = await run_loop(syllabus, ScriptedGenerator([BAD_ORDER, VALID]))
    assert outcome.converged
    assert outcome.n_cycles == 2
    assert outcome.violation_trajectory == [1, 0]


async def test_feedback_reaches_the_generator(syllabus: Syllabus) -> None:
    """Le 2e appel doit recevoir un feedback nommant la contrainte violee."""
    generator = ScriptedGenerator([BAD_ORDER, VALID])
    await run_loop(syllabus, generator)
    assert generator.calls[0] == ""
    assert "prerequisite" in generator.calls[1]
    assert "'A'" in generator.calls[1]


async def test_naive_feedback_says_nothing_specific(syllabus: Syllabus) -> None:
    generator = ScriptedGenerator([BAD_ORDER, VALID])
    await run_loop(syllabus, generator, feedback_builder=build_naive_feedback)
    assert "prerequisite" not in generator.calls[1]


async def test_loop_gives_up_after_max_cycles(syllabus: Syllabus) -> None:
    outcome = await run_loop(syllabus, ScriptedGenerator([BAD_ORDER] * 3), max_cycles=3)
    assert not outcome.converged
    assert outcome.n_cycles == 3
    assert outcome.final_plan is not None


async def test_malformed_json_is_counted_not_crashed(syllabus: Syllabus) -> None:
    outcome = await run_loop(syllabus, ScriptedGenerator(["pas du json", VALID]))
    assert outcome.converged
    assert outcome.cycles[0].error is not None
    assert outcome.cycles[1].result.is_valid


async def test_markdown_fenced_json_is_parsed(syllabus: Syllabus) -> None:
    outcome = await run_loop(syllabus, ScriptedGenerator([f"```json\n{VALID}\n```"]))
    assert outcome.converged


async def test_infeasible_instance_skips_the_llm() -> None:
    """Sur un syllabus cyclique, aucun appel LLM ne doit partir."""
    cyclic = Syllabus(
        objectives=(
            LearningObjective("A", "A", ("B",)),
            LearningObjective("B", "B", ("A",)),
        ),
        n_sessions=2,
        min_duration=1,
        max_duration=2,
    )
    generator = ScriptedGenerator([VALID])
    outcome = await run_loop(cyclic, generator)
    assert not outcome.converged
    assert outcome.infeasible_reasons
    assert generator.calls == []


async def test_llm_only_baseline_reports_violations(syllabus: Syllabus) -> None:
    outcome = await llm_only(syllabus, ScriptedGenerator([BAD_ORDER]))
    assert not outcome.converged
    assert outcome.cycles[0].n_violations == 1


def test_csp_only_baseline_is_valid_by_construction(syllabus: Syllabus) -> None:
    outcome = csp_only(syllabus)
    assert outcome.converged
    assert all(s.title.startswith("Session") for s in outcome.final_plan.sessions)


def test_build_feedback_is_empty_when_valid(syllabus: Syllabus) -> None:
    from m7_neurosymbolic.validator import Validator
    from m7_neurosymbolic.schema import PlanCandidate, Session

    plan = PlanCandidate((Session(0, "Bases", ("A",), 0, 1), Session(1, "Avance", ("B",), 1, 1)))
    assert build_feedback(Validator(syllabus).validate(plan)) == ""
