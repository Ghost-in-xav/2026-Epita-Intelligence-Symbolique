import json

from m1_pipeline.llm import OracleProvider, ScriptedProvider
from m1_pipeline.parsing import extract_json
from m1_pipeline.pipeline import run_pipeline
from m1_pipeline.problems import get_problem
from m1_pipeline.strategies import get_strategy


def test_extract_json_variants():
    assert extract_json('ANSWER: {"x": 1}') == {"x": 1}
    assert extract_json("```json\n{\"a\": true}\n```") == {"a": True}
    assert extract_json("blah {\"x\": 1} then {\"y\": 2}") == {"y": 2}  # last wins
    assert extract_json("no json here") is None


def test_oracle_solves_in_one_attempt():
    problem = get_problem("magic_square")
    run = run_pipeline(problem, OracleProvider(), get_strategy("direct"), max_attempts=3)
    assert run.solved
    assert run.n_attempts == 1


def test_reprompt_loop_recovers_after_failures():
    problem = get_problem("linear_arith")
    # Fail the first two attempts, succeed on the third.
    provider = OracleProvider(fail_first=2)
    run = run_pipeline(problem, provider, get_strategy("counterexample"), max_attempts=5)
    assert run.solved
    assert run.n_attempts == 3
    assert not run.attempts[0].result.ok
    assert run.attempts[-1].result.ok


def test_scripted_provider_drives_exact_sequence():
    problem = get_problem("knights_knaves")
    good = json.dumps({"A": True, "B": False, "C": False})
    provider = ScriptedProvider(["not json", "ANSWER: " + good])
    run = run_pipeline(problem, provider, get_strategy("counterexample"), max_attempts=3)
    assert run.n_attempts == 2
    assert run.attempts[0].result.error_category == "parse_error"
    assert run.solved


def test_unsat_problem_never_solved_but_runs_complete():
    problem = get_problem("unsat_trap")
    run = run_pipeline(problem, OracleProvider(), get_strategy("counterexample"), max_attempts=3)
    assert not run.solved
    assert run.n_attempts == 3  # exhausts attempts, never accepts
