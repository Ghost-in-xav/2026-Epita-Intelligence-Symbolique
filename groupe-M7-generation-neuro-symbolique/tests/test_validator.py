"""Tests du validateur : l'oracle du projet, teste sans LLM."""

from __future__ import annotations

import pytest

from m7_neurosymbolic.schema import (
    LearningObjective,
    PlanCandidate,
    Session,
    Syllabus,
    ViolationKind,
)
from m7_neurosymbolic.validator import Validator


@pytest.fixture
def syllabus() -> Syllabus:
    """A, puis B qui depend de A."""
    return Syllabus(
        objectives=(
            LearningObjective("A", "Bases"),
            LearningObjective("B", "Avance", ("A",)),
        ),
        n_sessions=2,
        min_duration=1,
        max_duration=2,
    )


def plan_of(*sessions: Session) -> PlanCandidate:
    return PlanCandidate(sessions=sessions)


def kinds(result) -> set[ViolationKind]:
    return {v.kind for v in result.violations}


def test_valid_plan_passes(syllabus: Syllabus) -> None:
    plan = plan_of(
        Session(0, "Bases", ("A",), 0, 1),
        Session(1, "Avance", ("B",), 1, 1),
    )
    result = Validator(syllabus).validate(plan)
    assert result.is_valid, result.summary()


def test_missing_objective(syllabus: Syllabus) -> None:
    plan = plan_of(Session(0, "Bases", ("A",), 0, 1))
    result = Validator(syllabus).validate(plan)
    assert ViolationKind.COVERAGE in kinds(result)
    assert any("B" in v.involved for v in result.violations)


def test_prerequisite_order(syllabus: Syllabus) -> None:
    """B avant A."""
    plan = plan_of(
        Session(0, "Avance", ("B",), 0, 1),
        Session(1, "Bases", ("A",), 1, 1),
    )
    assert ViolationKind.PREREQUISITE in kinds(Validator(syllabus).validate(plan))


def test_overlap(syllabus: Syllabus) -> None:
    plan = plan_of(
        Session(0, "Bases", ("A",), 0, 2),
        Session(1, "Avance", ("B",), 1, 1),
    )
    assert ViolationKind.OVERLAP in kinds(Validator(syllabus).validate(plan))


def test_duration_bounds(syllabus: Syllabus) -> None:
    plan = plan_of(
        Session(0, "Bases", ("A",), 0, 5),
        Session(1, "Avance", ("B",), 5, 1),
    )
    assert ViolationKind.DURATION in kinds(Validator(syllabus).validate(plan))


def test_hallucinated_objective(syllabus: Syllabus) -> None:
    plan = plan_of(
        Session(0, "Bases", ("A",), 0, 1),
        Session(1, "Avance", ("B", "ZZZ"), 1, 1),
    )
    assert ViolationKind.UNKNOWN_OBJECTIVE in kinds(Validator(syllabus).validate(plan))


def test_feasible_instance(syllabus: Syllabus) -> None:
    feasible, reasons = Validator(syllabus).is_instance_feasible()
    assert feasible
    assert reasons == []


def test_prerequisite_cycle_is_infeasible() -> None:
    """Cycle A -> B -> A : aucun plan n'existe, la boucle ne doit pas etre lancee."""
    cyclic = Syllabus(
        objectives=(
            LearningObjective("A", "A", ("B",)),
            LearningObjective("B", "B", ("A",)),
        ),
        n_sessions=2,
        min_duration=1,
        max_duration=2,
    )
    feasible, reasons = Validator(cyclic).is_instance_feasible()
    assert not feasible
    assert reasons


def test_csp_solve_produces_valid_plan(syllabus: Syllabus) -> None:
    validator = Validator(syllabus)
    plan = validator.solve()
    assert plan is not None
    assert validator.validate(plan).is_valid
