"""Tests unitaires des outils symboliques (fonctions pures, sans MCP)."""

from symbolic_mcp.tools import owl_reason, solve_sat, solve_smt

# --------------------------------------------------------------------------- #
# SAT
# --------------------------------------------------------------------------- #
def test_sat_satisfiable():
    # (a OR b) AND (NOT a OR c) AND (NOT b)  ->  a=True, b=False, c=True
    r = solve_sat([[1, 2], [-1, 3], [-2]], var_names={"1": "a", "2": "b", "3": "c"})
    assert r["status"] == "SAT"
    model = r["models"][0]
    assert model["a"] is True and model["b"] is False and model["c"] is True


def test_sat_unsat():
    r = solve_sat([[1], [-1]])
    assert r["status"] == "UNSAT"
    assert r["models"] == []


def test_sat_enumerate_models():
    # (a OR b) a 3 modeles satisfaisants
    r = solve_sat([[1, 2]], max_models=10)
    assert r["status"] == "SAT"
    assert len(r["models"]) == 3


def test_sat_invalid_input():
    assert solve_sat([]).get("ok") is False
    assert solve_sat([[1, 0]]).get("ok") is False  # 0 interdit en DIMACS


def test_sat_rejects_invalid_assumptions():
    assert solve_sat([[1]], assumptions=[0]).get("ok") is False
    assert solve_sat([[1]], assumptions=["1"]).get("ok") is False


# --------------------------------------------------------------------------- #
# SMT
# --------------------------------------------------------------------------- #
def test_smt_sat_with_model():
    r = solve_smt(
        "(declare-const x Int)(declare-const y Int)"
        "(assert (> x 0))(assert (= (+ x y) 10))(assert (< y x))"
    )
    assert r["status"] == "sat"
    assert "x" in r["model"] and "y" in r["model"]


def test_smt_unsat():
    r = solve_smt("(declare-const x Int)(assert (> x 5))(assert (< x 2))")
    assert r["status"] == "unsat"


def test_smt_parse_error():
    r = solve_smt("(this is not valid smtlib")
    assert r.get("ok") is False


# --------------------------------------------------------------------------- #
# OWL (HermiT ; necessite Java)
# --------------------------------------------------------------------------- #
_TTL = """@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix : <http://ex.org/o#> .
:Animal a owl:Class .
:Mammal a owl:Class ; rdfs:subClassOf :Animal .
:Dog a owl:Class ; rdfs:subClassOf :Mammal .
:rex a :Dog ."""

_TTL_INCONSISTENT = _TTL + """
:Plant a owl:Class .
:Animal owl:disjointWith :Plant .
:rex a :Plant ."""


def test_owl_consistent_and_classify():
    r = owl_reason(_TTL, fmt="turtle", operation="classify")
    assert r["consistent"] is True
    # rex, individu de Dog, doit heriter Mammal et Animal par inference
    assert set(r["individual_types"]["rex"]) >= {"Dog", "Mammal", "Animal"}
    assert r["class_hierarchy"]["Dog"] == ["Mammal"]


def test_owl_inconsistent():
    r = owl_reason(_TTL_INCONSISTENT, fmt="turtle")
    assert r["consistent"] is False


def test_owl_query_class():
    r = owl_reason(_TTL, fmt="turtle", operation="query", target="Dog")
    assert set(r["focus"]["inferred_superclasses"]) >= {"Mammal", "Animal"}


def test_owl_rejects_unknown_operation():
    r = owl_reason(_TTL, fmt="turtle", operation="typo")
    assert r.get("ok") is False
    assert "operation" in r["error"].lower()


def test_owl_query_requires_target():
    r = owl_reason(_TTL, fmt="turtle", operation="query")
    assert r.get("ok") is False
    assert "target" in r["error"].lower()


def test_owl_removes_temporary_file_after_success(tmp_path, monkeypatch):
    import symbolic_mcp.tools.owl_tool as owl_tool

    monkeypatch.setattr(owl_tool.tempfile, "tempdir", str(tmp_path))
    assert owl_reason(_TTL, fmt="turtle")["ok"] is True
    assert list(tmp_path.glob("*.owl")) == []


def test_owl_removes_temporary_file_after_load_error(tmp_path, monkeypatch):
    import symbolic_mcp.tools.owl_tool as owl_tool

    monkeypatch.setattr(owl_tool.tempfile, "tempdir", str(tmp_path))
    assert owl_reason("not rdf/xml", fmt="rdfxml")["ok"] is False
    assert list(tmp_path.glob("*.owl")) == []
