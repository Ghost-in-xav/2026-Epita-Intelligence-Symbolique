"""Tests du scoring de la chaine LLM vers outils symboliques."""

from eval.run_eval import score
from symbolic_mcp.host.gemini_host import ChainResult


def _result(answer: str) -> ChainResult:
    return ChainResult("", answer, [{"tool": "smt_solve", "status": "sat"}])


def test_score_requires_every_answer_marker():
    entry = {
        "expect_tool": "smt_solve",
        "expect_status": "sat",
        "expect_answer": ["7", "3"],
    }

    assert score(entry, _result("7 seulement"))["answer_ok"] is False
    assert score(entry, _result("x vaut 7 et y vaut 3"))["answer_ok"] is True


def test_score_accepts_alternatives_within_one_marker():
    entry = {
        "expect_tool": "smt_solve",
        "expect_status": "sat",
        "expect_answer": [["non", "impossible", "aucun"]],
    }

    assert score(entry, _result("C'est impossible"))["answer_ok"] is True
