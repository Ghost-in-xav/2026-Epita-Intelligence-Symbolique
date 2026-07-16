from m1_pipeline.problems import ALL_PROBLEMS, get_problem
from m1_pipeline.verifier import Status, solve, verify


def test_solver_accepts_its_own_solution_for_sat_problems():
    for problem in ALL_PROBLEMS:
        model = solve(problem)
        if problem.satisfiable:
            assert model is not None, problem.id
            res = verify(problem, model)
            assert res.status is Status.ACCEPTED, (problem.id, res.message, res.violated)
        else:
            assert model is None, problem.id


def test_constraint_violation_is_reported():
    p = get_problem("linear_arith")
    res = verify(p, {"x": 0, "y": 0, "z": 0})
    assert res.status is Status.CONSTRAINT_VIOLATION
    assert res.violated  # at least one constraint listed


def test_schema_error_on_missing_and_wrong_type():
    p = get_problem("knights_knaves")
    assert verify(p, {"A": True, "B": False}).status is Status.SCHEMA_ERROR  # missing C
    assert verify(p, {"A": 1, "B": False, "C": True}).status is Status.SCHEMA_ERROR  # int for bool


def test_parse_error_on_none():
    p = get_problem("scheduling")
    assert verify(p, None).status is Status.PARSE_ERROR


def test_unsat_problem_rejects_every_assignment():
    p = get_problem("unsat_trap")
    for a in (1, 2):
        for b in (1, 2):
            for c in (1, 2):
                assert not verify(p, {"a": a, "b": b, "c": c}).ok
