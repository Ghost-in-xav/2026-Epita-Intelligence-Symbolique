"""Serveur MCP exposant les outils d'analyse symbolique.

Lance un serveur Model Context Protocol (transport stdio par defaut) qui publie
trois outils symboliques — `sat_solve` (SAT), `smt_solve` (SMT), `owl_reason`
(OWL) — plus des outils de gestion de session. N'importe quel hote MCP
(l'hote Gemini de ce projet, MCP Inspector, ou tout autre hote MCP) peut s'y connecter.

Lancement :
    python -m symbolic_mcp.server          # transport stdio
    mcp dev src/symbolic_mcp/server.py     # via l'inspecteur MCP
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .session import SessionManager
from .tools import owl_reason as _owl_reason
from .tools import solve_sat as _solve_sat
from .tools import solve_smt as _solve_smt

mcp = FastMCP(
    "symbolic-analysis",
    instructions=(
        "Serveur d'outils d'analyse symbolique. Traduis le probleme en langage "
        "naturel vers la representation formelle attendue par l'outil (CNF DIMACS "
        "pour sat_solve, SMT-LIB2 pour smt_solve, OWL RDF/XML ou Turtle pour "
        "owl_reason), appelle l'outil, puis reformule le resultat symbolique en "
        "langage naturel. Ouvre une session avec open_session pour tracer une "
        "chaine de raisonnement multi-etapes."
    ),
)

sessions = SessionManager()


def _unknown_session_error(session_id: str | None) -> dict[str, Any] | None:
    if session_id and sessions.get(session_id) is None:
        return {
            "ok": False,
            "error": f"Session '{session_id}' inconnue.",
        }
    return None


def _log(session_id: str | None, tool: str, args_summary: str, result: dict[str, Any]) -> None:
    if not session_id:
        return
    session = sessions.get(session_id)
    if session is not None:
        session.log(tool, args_summary, str(result.get("summary") or result.get("error", "")))


# --------------------------------------------------------------------------- #
# Gestion de session / contexte
# --------------------------------------------------------------------------- #
@mcp.tool()
def open_session() -> dict[str, Any]:
    """Ouvre une session de raisonnement et renvoie son identifiant.

    Passe ensuite ce `session_id` aux outils symboliques pour journaliser la
    chaine d'appels (tracabilite de la chaine LLM -> outil symbolique).
    """
    session = sessions.create()
    return {
        "ok": True,
        "session_id": session.id,
        "summary": f"Session {session.id} ouverte. Transmets ce session_id aux outils "
        "pour tracer ta chaine de raisonnement.",
    }


@mcp.tool()
def session_history(session_id: str) -> dict[str, Any]:
    """Renvoie le journal (contexte) d'une session : outils appeles et resultats."""
    session = sessions.get(session_id)
    if session is None:
        return {"ok": False, "error": f"Session '{session_id}' inconnue."}
    return {"ok": True, **session.snapshot()}


# --------------------------------------------------------------------------- #
# Outils symboliques
# --------------------------------------------------------------------------- #
@mcp.tool()
def sat_solve(
    clauses: list[list[int]],
    assumptions: list[int] | None = None,
    var_names: dict[str, str] | None = None,
    max_models: int = 1,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Resout un probleme SAT booleen en CNF (format DIMACS) avec PySAT.

    Chaque clause est une liste d'entiers non nuls : `i` = variable i vraie,
    `-i` = variable i fausse (variables indexees a partir de 1). Renvoie SAT
    (avec un ou plusieurs modeles) ou UNSAT. `var_names` permet d'obtenir un
    modele lisible (ex. {"1": "pluie", "2": "parapluie"}).
    """
    if error := _unknown_session_error(session_id):
        return error
    result = _solve_sat(clauses, assumptions=assumptions, var_names=var_names, max_models=max_models)
    _log(session_id, "sat_solve", f"{len(clauses)} clauses", result)
    return result


@mcp.tool()
def smt_solve(
    smtlib2: str,
    get_model: bool = True,
    timeout_ms: int = 10000,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Verifie la satisfiabilite de contraintes SMT-LIB2 avec Z3 (theories : Int,
    Real, Bool, arrays, bit-vectors...).

    Fournir le probleme au format SMT-LIB 2 (declarations + assertions). Renvoie
    sat / unsat / unknown et, si sat, un modele temoin.
    """
    if error := _unknown_session_error(session_id):
        return error
    result = _solve_smt(smtlib2, get_model=get_model, timeout_ms=timeout_ms)
    _log(session_id, "smt_solve", f"{len(smtlib2)} caracteres SMT-LIB2", result)
    return result


@mcp.tool()
def owl_reason(
    ontology: str,
    fmt: str = "rdfxml",
    operation: str = "consistency",
    target: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Raisonne sur une ontologie OWL avec le reasoner HermiT (via owlready2).

    Verifie la coherence, detecte les classes insatisfiables, et infere la
    hierarchie de classes et les types des individus. `fmt` = "rdfxml" ou
    "turtle". `operation` = "consistency" | "classify" | "query" (avec `target`).
    """
    if error := _unknown_session_error(session_id):
        return error
    result = _owl_reason(ontology, fmt=fmt, operation=operation, target=target)
    _log(session_id, "owl_reason", f"operation={operation}", result)
    return result


def main() -> None:
    """Point d'entree : demarre le serveur MCP en transport stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
