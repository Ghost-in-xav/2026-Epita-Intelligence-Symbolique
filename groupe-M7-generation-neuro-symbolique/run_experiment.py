"""Compare les approches sur N executions et ecrit les resultats dans results/.

Usage : python run_experiment.py --runs 5
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, "src")

from m7_neurosymbolic.baselines import csp_only, llm_only  # noqa: E402
from m7_neurosymbolic.feedback import build_feedback, build_naive_feedback  # noqa: E402
from m7_neurosymbolic.generator import SemanticKernelGenerator  # noqa: E402
from m7_neurosymbolic.loop import LoopOutcome, run_loop  # noqa: E402
from m7_neurosymbolic.metrics import summarize  # noqa: E402
from m7_neurosymbolic.schema import Syllabus  # noqa: E402


def outcome_to_dict(outcome: LoopOutcome) -> dict:
    """Les objectifs couverts suffisent a caracteriser un run.

    On ne garde pas les plans complets : 30 plans representent des milliers de lignes que
    personne ne relit. Un exemple par configuration est joint separement.
    """
    covered = (
        sorted({o for s in outcome.final_plan.sessions for o in s.objectives})
        if outcome.final_plan
        else []
    )
    return {
        "converged": outcome.converged,
        "n_cycles": outcome.n_cycles,
        "violation_trajectory": outcome.violation_trajectory,
        "objectives_covered": covered,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--max-cycles", type=int, default=5)
    parser.add_argument("--syllabus", default="data/syllabus.json")
    args = parser.parse_args()

    load_dotenv(".env")
    syllabus = Syllabus.from_json(args.syllabus)

    # Un generateur neuf par run : sinon l'historique d'un run pollue le suivant.
    configs = {
        "targeted": build_feedback,
        "naive": build_naive_feedback,
    }

    results: dict[str, object] = {}

    for name, builder in configs.items():
        outcomes = await asyncio.gather(
            *(
                run_loop(
                    syllabus,
                    SemanticKernelGenerator(),
                    max_cycles=args.max_cycles,
                    feedback_builder=builder,
                )
                for _ in range(args.runs)
            )
        )
        report = summarize(list(outcomes))
        print(f"{name:10} {report.render()}")
        example = next((o.final_plan for o in outcomes if o.final_plan), None)
        results[name] = {
            "report": report.__dict__,
            "runs": [outcome_to_dict(o) for o in outcomes],
            "example_final_plan": json.loads(example.to_json()) if example else None,
        }

    llm_outcomes = await asyncio.gather(
        *(llm_only(syllabus, SemanticKernelGenerator()) for _ in range(args.runs))
    )
    llm_report = summarize(list(llm_outcomes))
    print(f"{'llm_only':10} {llm_report.render()}")
    llm_example = next((o.final_plan for o in llm_outcomes if o.final_plan), None)
    results["llm_only"] = {
        "report": llm_report.__dict__,
        "runs": [outcome_to_dict(o) for o in llm_outcomes],
        "example_final_plan": json.loads(llm_example.to_json()) if llm_example else None,
    }

    csp = csp_only(syllabus)
    print(f"{'csp_only':10} valide={csp.converged} (par construction)")
    # Le plan CSP est garde en entier : ses intitules generiques sont le point de comparaison.
    results["csp_only"] = {
        **outcome_to_dict(csp),
        "final_plan": json.loads(csp.final_plan.to_json()) if csp.final_plan else None,
    }

    Path("results").mkdir(exist_ok=True)
    Path("results/experiment.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("\nresults/experiment.json ecrit")


if __name__ == "__main__":
    asyncio.run(main())
