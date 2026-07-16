"""Hote Gemini <-> serveur MCP d'analyse symbolique.

Ce module implemente le pattern *tool-augmented generation* : Gemini reçoit un
probleme en langage naturel, le traduit vers la representation formelle attendue
(CNF, SMT-LIB2, OWL), appelle l'outil symbolique via MCP, puis reformule le
resultat. Chaque appel est trace (nom de l'outil, arguments, resume du resultat)
pour rendre la chaine de raisonnement observable et evaluable.

Usage :
    # Necessite la variable d'environnement GEMINI_API_KEY (clef Google AI Studio)
    python -m symbolic_mcp.host.gemini_host --prompt "Anne, Bob et Chloe ..."
    python -m symbolic_mcp.host.gemini_host --self-test   # sans LLM : verifie le pont MCP
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..config import gemini_api_key, gemini_model

SYSTEM_INSTRUCTION = (
    "Tu es un agent de raisonnement qui DELEGUE toute deduction logique a des "
    "outils symboliques exacts, au lieu de raisonner 'de tete'. Regles :\n"
    "- Probleme de logique booleenne / contraintes vrai-faux -> traduis en CNF "
    "(clauses DIMACS) et appelle sat_solve.\n"
    "- Probleme arithmetique / entiers / reels / egalites-inegalites -> traduis "
    "en SMT-LIB2 et appelle smt_solve.\n"
    "- Probleme d'ontologie / classes / coherence / subsomption -> ecris une "
    "ontologie OWL (Turtle) et appelle owl_reason.\n"
    "Apres l'appel, fonde ta reponse UNIQUEMENT sur le resultat de l'outil, et "
    "explique brievement la traduction effectuee. Si l'outil renvoie une erreur, "
    "corrige ta formalisation et reessaie."
)

# Repertoire `src/` a mettre dans PYTHONPATH pour lancer le serveur en sous-processus.
_SRC_DIR = str(Path(__file__).resolve().parents[2])


def _strip_schema(node: Any) -> Any:
    """Nettoie un JSON Schema pour l'API Gemini :
    - retire les metadonnees inutiles voire genantes (title/default) ;
    - aplatit les types optionnels `anyOf: [T, {"type": "null"}]` en `T`
      (les champs optionnels Pydantic produisent ce motif)."""
    if isinstance(node, dict):
        if "anyOf" in node:
            branches = [
                b
                for b in node["anyOf"]
                if not (isinstance(b, dict) and b.get("type") == "null")
            ]
            if len(branches) == 1:
                merged = dict(branches[0])
                if "description" in node and "description" not in merged:
                    merged["description"] = node["description"]
                return _strip_schema(merged)
        return {
            k: _strip_schema(v)
            for k, v in node.items()
            if k not in ("title", "default")
        }
    if isinstance(node, list):
        return [_strip_schema(v) for v in node]
    return node


def _extract_tool_result(call_result) -> dict[str, Any]:
    """CallToolResult -> dict Python renvoye par l'outil."""
    sc = getattr(call_result, "structuredContent", None)
    if isinstance(sc, dict):
        return sc.get("result", sc)
    content = getattr(call_result, "content", None) or []
    if content and getattr(content[0], "text", None):
        try:
            return json.loads(content[0].text)
        except json.JSONDecodeError:
            return {"raw": content[0].text}
    return {"error": "resultat d'outil vide"}


@dataclass
class ChainResult:
    """Resultat d'une execution de la chaine LLM -> outils."""

    prompt: str
    answer: str
    trace: list[dict[str, Any]] = field(default_factory=list)
    n_tool_calls: int = 0
    error: str | None = None

    def pretty(self) -> str:
        lines = [f"PROMPT : {self.prompt}", ""]
        for i, step in enumerate(self.trace, 1):
            lines.append(f"  [{i}] {step['tool']}({step['arguments']})")
            lines.append(f"      -> {step['result']}")
        lines.append("")
        lines.append(f"REPONSE : {self.answer}")
        return "\n".join(lines)


class GeminiMCPHost:
    """Connecte Gemini au serveur MCP et execute des chaines de raisonnement."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        max_steps: int = 6,
    ) -> None:
        self.model = model or gemini_model()
        self.max_steps = max_steps
        self._api_key = api_key or gemini_api_key()

    def _server_params(self) -> StdioServerParameters:
        env = dict(os.environ)
        env["PYTHONPATH"] = _SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        return StdioServerParameters(
            command=sys.executable,
            args=["-m", "symbolic_mcp.server"],
            env=env,
        )

    async def list_tool_declarations(self) -> list[dict[str, Any]]:
        """Se connecte au serveur MCP et renvoie les declarations d'outils
        (nom, description, schema nettoye) — utile pour un test hors-LLM."""
        async with stdio_client(self._server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                return [
                    {
                        "name": t.name,
                        "description": (t.description or "").strip(),
                        "parameters_json_schema": _strip_schema(t.inputSchema),
                    }
                    for t in tools.tools
                ]

    async def run(self, prompt: str) -> ChainResult:
        """Execute la chaine : Gemini planifie, appelle les outils MCP, conclut."""
        if not self._api_key:
            return ChainResult(
                prompt=prompt,
                answer="",
                error="GEMINI_API_KEY (ou GOOGLE_API_KEY) non definie. "
                "Cree une clef gratuite sur https://aistudio.google.com/apikey",
            )

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self._api_key)

        async with stdio_client(self._server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                mcp_tools = (await session.list_tools()).tools
                declarations = [
                    types.FunctionDeclaration(
                        name=t.name,
                        description=(t.description or "").strip(),
                        parameters_json_schema=_strip_schema(t.inputSchema),
                    )
                    for t in mcp_tools
                ]
                config = types.GenerateContentConfig(
                    tools=[types.Tool(function_declarations=declarations)],
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                )
                contents: list[Any] = [
                    types.Content(role="user", parts=[types.Part(text=prompt)])
                ]
                trace: list[dict[str, Any]] = []

                for _ in range(self.max_steps):
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model=self.model,
                        contents=contents,
                        config=config,
                    )
                    candidate = response.candidates[0]
                    contents.append(candidate.content)
                    calls = [
                        p.function_call
                        for p in (candidate.content.parts or [])
                        if getattr(p, "function_call", None)
                    ]
                    if not calls:
                        return ChainResult(
                            prompt=prompt,
                            answer=(response.text or "").strip(),
                            trace=trace,
                            n_tool_calls=len(trace),
                        )

                    tool_result_parts = []
                    for call in calls:
                        args = dict(call.args or {})
                        mcp_result = await session.call_tool(call.name, args)
                        data = _extract_tool_result(mcp_result)
                        trace.append(
                            {
                                "tool": call.name,
                                "arguments": _short(args),
                                "result": data.get("summary") or data.get("error") or str(data)[:200],
                                "status": _status_of(data),
                            }
                        )
                        tool_result_parts.append(
                            types.Part.from_function_response(
                                name=call.name, response={"result": data}
                            )
                        )
                    contents.append(types.Content(role="user", parts=tool_result_parts))

                return ChainResult(
                    prompt=prompt,
                    answer="(nombre maximal d'etapes atteint sans reponse finale)",
                    trace=trace,
                    n_tool_calls=len(trace),
                    error="max_steps",
                )


def _short(args: dict[str, Any], limit: int = 90) -> str:
    text = ", ".join(f"{k}={v!r}" for k, v in args.items() if k != "session_id")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _status_of(data: dict[str, Any]) -> str | None:
    """Statut symbolique normalise d'un resultat d'outil (pour l'evaluation)."""
    if "status" in data:  # sat_solve -> SAT/UNSAT ; smt_solve -> sat/unsat/unknown
        return str(data["status"])
    if "consistent" in data:  # owl_reason
        return "consistent" if data["consistent"] else "inconsistent"
    return None


async def _self_test() -> int:
    """Verifie le pont MCP sans appeler le LLM (aucune clef requise)."""
    host = GeminiMCPHost()
    decls = await host.list_tool_declarations()
    print(f"Connexion au serveur MCP OK — {len(decls)} outils exposes a Gemini :")
    for d in decls:
        required = d["parameters_json_schema"].get("required", [])
        print(f"  - {d['name']}  (args requis : {', '.join(required) or 'aucun'})")
    expected = {"sat_solve", "smt_solve", "owl_reason", "open_session", "session_history"}
    got = {d["name"] for d in decls}
    ok = expected <= got
    print("\nSchemas convertis pour Gemini :", "OK" if ok else f"MANQUE {expected - got}")
    return 0 if ok else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Hote Gemini pour le serveur MCP symbolique")
    parser.add_argument("--prompt", help="Question en langage naturel a resoudre")
    parser.add_argument("--model", default=gemini_model())
    parser.add_argument("--self-test", action="store_true", help="Teste le pont MCP sans LLM")
    args = parser.parse_args()

    if args.self_test:
        raise SystemExit(asyncio.run(_self_test()))

    if not args.prompt:
        parser.error("fournir --prompt \"...\" ou --self-test")

    host = GeminiMCPHost(model=args.model)
    result = asyncio.run(host.run(args.prompt))
    if result.error and not result.trace:
        print("ERREUR :", result.error)
        raise SystemExit(1)
    print(result.pretty())


if __name__ == "__main__":
    main()
