"""Test d'integration de la couche MCP.

On connecte un client MCP au serveur *en memoire* (sans sous-processus ni LLM)
via l'utilitaire de test du SDK, puis on liste et on appelle les outils comme le
ferait un vrai hote MCP (Gemini, MCP Inspector...).
"""

import asyncio
import json
import subprocess
import sys

from mcp.shared.memory import create_connected_server_and_client_session

from symbolic_mcp.server import mcp


def _extract(call_result) -> dict:
    """Recupere le dict renvoye par l'outil depuis un CallToolResult."""
    if getattr(call_result, "structuredContent", None):
        sc = call_result.structuredContent
        return sc.get("result", sc) if isinstance(sc, dict) else sc
    return json.loads(call_result.content[0].text)


async def _list_and_call(name: str, args: dict) -> dict:
    async with create_connected_server_and_client_session(mcp._mcp_server) as client:
        tools = await client.list_tools()
        names = {t.name for t in tools.tools}
        assert {"sat_solve", "smt_solve", "owl_reason", "open_session"} <= names
        result = await client.call_tool(name, args)
        return _extract(result)


def test_mcp_lists_and_calls_sat():
    data = asyncio.run(_list_and_call("sat_solve", {"clauses": [[1, 2], [-2]]}))
    assert data["status"] == "SAT"


def test_mcp_calls_smt():
    data = asyncio.run(
        _list_and_call("smt_solve", {"smtlib2": "(declare-const x Int)(assert (> x 3))"})
    )
    assert data["status"] == "sat"


def test_mcp_session_flow():
    async def flow():
        async with create_connected_server_and_client_session(mcp._mcp_server) as client:
            opened = _extract(await client.call_tool("open_session", {}))
            sid = opened["session_id"]
            await client.call_tool("sat_solve", {"clauses": [[1]], "session_id": sid})
            hist = _extract(await client.call_tool("session_history", {"session_id": sid}))
            return hist

    hist = asyncio.run(flow())
    assert hist["n_calls"] == 1
    assert hist["history"][0]["tool"] == "sat_solve"


def test_mcp_rejects_unknown_session_before_solving():
    data = asyncio.run(
        _list_and_call(
            "sat_solve",
            {"clauses": [[0]], "session_id": "missing-session"},
        )
    )
    assert data["ok"] is False
    assert "session" in data["error"].lower()
    assert "inconnue" in data["error"].lower()


def test_host_package_does_not_eagerly_import_gemini_module():
    code = (
        "import sys; sys.path.insert(0, 'src'); import symbolic_mcp.host; "
        "assert 'symbolic_mcp.host.gemini_host' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stderr


if __name__ == "__main__":
    test_mcp_lists_and_calls_sat()
    test_mcp_calls_smt()
    test_mcp_session_flow()
    print("OK")
