"""Harnais d'evaluation de la chaine LLM -> outil symbolique.

Pour chaque probleme du benchmark (langage naturel + verite terrain), on execute
la chaine complete via l'hote Gemini, puis on mesure trois niveaux de precision :

- selection_ok  : le LLM a-t-il appele le BON outil symbolique ?
- symbolic_ok   : cet outil a-t-il renvoye le BON statut (SAT/UNSAT/coherent...) ?
- answer_ok     : la reponse finale en langage naturel est-elle correcte ?
- chain_ok      : les trois a la fois (chaine de bout en bout correcte).

Necessite GEMINI_API_KEY. Lancement :
    python eval/run_eval.py                 # tout le benchmark
    python eval/run_eval.py --limit 3       # premiers items
    python eval/run_eval.py --model gemini-2.0-flash
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from symbolic_mcp.config import gemini_model  # noqa: E402
from symbolic_mcp.host.gemini_host import ChainResult, GeminiMCPHost  # noqa: E402

BENCHMARK = Path(__file__).resolve().parent / "benchmark.jsonl"


def load_benchmark(path: Path = BENCHMARK) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def score(entry: dict, result: ChainResult) -> dict:
    """Compare le resultat de la chaine a la verite terrain de l'item."""
    expected_tool = entry.get("expect_tool")
    expected_status = (entry.get("expect_status") or "").lower()
    expected_answer_groups = [
        [marker.lower()]
        if isinstance(marker, str)
        else [alternative.lower() for alternative in marker]
        for marker in entry.get("expect_answer", [])
    ]

    called_steps = [s for s in result.trace if s.get("tool") == expected_tool]
    selection_ok = bool(called_steps)
    symbolic_ok = (
        any((s.get("status") or "").lower() == expected_status for s in called_steps)
        if expected_status
        else selection_ok
    )
    answer_lc = (result.answer or "").lower()
    answer_ok = (
        all(
            bool(group) and any(token in answer_lc for token in group)
            for group in expected_answer_groups
        )
        if expected_answer_groups
        else True
    )
    return {
        "selection_ok": selection_ok,
        "symbolic_ok": symbolic_ok,
        "answer_ok": answer_ok,
        "chain_ok": selection_ok and symbolic_ok and answer_ok,
    }


def _pct(n: int, d: int) -> str:
    return f"{100.0 * n / d:5.1f}%" if d else "  n/a"


async def evaluate(model: str, limit: int | None) -> dict:
    benchmark = load_benchmark()
    if limit:
        benchmark = benchmark[:limit]
    host = GeminiMCPHost(model=model)

    results = []
    print(f"Evaluation de {len(benchmark)} problemes (modele : {model})\n")
    for entry in benchmark:
        result = await host.run(entry["prompt"])
        sc = score(entry, result)
        results.append({"id": entry["id"], "category": entry["category"], **sc,
                        "answer": result.answer, "n_tool_calls": result.n_tool_calls})
        flag = "OK " if sc["chain_ok"] else "-- "
        print(f"  {flag} {entry['id']:<7} sel={int(sc['selection_ok'])} "
              f"sym={int(sc['symbolic_ok'])} ans={int(sc['answer_ok'])}")

    metrics = ["selection_ok", "symbolic_ok", "answer_ok", "chain_ok"]
    by_cat: dict[str, list] = defaultdict(list)
    for r in results:
        by_cat[r["category"]].append(r)

    print("\n=== Precision par categorie ===")
    header = f"{'categorie':<10} {'n':>3} " + " ".join(f"{m.split('_')[0]:>9}" for m in metrics)
    print(header)
    summary = {}
    for cat, rows in sorted(by_cat.items()):
        cells = " ".join(_pct(sum(r[m] for r in rows), len(rows)) for m in metrics)
        print(f"{cat:<10} {len(rows):>3} {cells}")
        summary[cat] = {m: sum(r[m] for r in rows) / len(rows) for m in metrics}
    total = " ".join(_pct(sum(r[m] for r in results), len(results)) for m in metrics)
    print(f"{'TOTAL':<10} {len(results):>3} {total}")
    summary["_total"] = {m: sum(r[m] for r in results) / len(results) for m in metrics}

    out = Path(__file__).resolve().parent / "results.json"
    out.write_text(json.dumps({"model": model, "summary": summary, "items": results},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDetails ecrits dans {out}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluation de la chaine LLM -> outils symboliques")
    parser.add_argument("--model", default=gemini_model())
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    if not GeminiMCPHost()._api_key:
        print("GEMINI_API_KEY (ou GOOGLE_API_KEY) non definie.\n"
              "Cree une clef gratuite sur https://aistudio.google.com/apikey puis :\n"
              "  export GEMINI_API_KEY=...", file=sys.stderr)
        raise SystemExit(1)

    asyncio.run(evaluate(args.model, args.limit))


if __name__ == "__main__":
    main()
