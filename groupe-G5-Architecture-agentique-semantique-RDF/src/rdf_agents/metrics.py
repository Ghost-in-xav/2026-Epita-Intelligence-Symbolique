"""Couche d'évaluation de l'architecture.

Trois familles de métriques, conformément au sujet :

* **débit** : documents/s et triplets/s, globalement et par agent ;
* **couverture de validation** : shapes évaluées, taux de conformité,
  violations par sévérité ;
* **qualité du raisonnement** : triplets inférés, ratio d'inférence,
  inconsistances détectées, liens ``owl:sameAs`` produits.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List

from .blackboard import Blackboard
from .events import (INCONSISTENCY_DETECTED, LINKING_COMPLETED, TRIPLES_INFERRED,
                     VALIDATION_SUCCEEDED, VIOLATION_DETECTED)


def evaluate(blackboard: Blackboard, trace: List[dict],
             agents: List) -> Dict[str, dict]:
    events = blackboard.bus.log

    # ------------------------------------------------------------------ débit
    total_seconds = sum(r["seconds"] for r in trace) or 1e-9
    total_triples = sum(r["triples"] for r in trace)
    per_agent_time = defaultdict(float)
    per_agent_calls = Counter()
    for agent in agents:
        for action, _doc, seconds in agent.timings:
            per_agent_time[f"{agent.name}:{action}"] += seconds
            per_agent_calls[f"{agent.name}:{action}"] += 1

    throughput = {
        "documents": len(trace),
        "documents_per_second": round(len(trace) / total_seconds, 2),
        "asserted_triples": total_triples,
        "triples_per_second": round(total_triples / total_seconds, 1),
        "total_pipeline_seconds": round(total_seconds, 3),
        "per_agent_seconds": {k: round(v, 4) for k, v in sorted(per_agent_time.items())},
        "per_agent_calls": dict(per_agent_calls),
    }

    # ------------------------------------------------- couverture de validation
    validations = [e for e in events if e.type == VALIDATION_SUCCEEDED]
    violations = [e for e in events if e.type == VIOLATION_DETECTED]
    validated_docs = {e.document for e in validations} | {e.document for e in violations}
    severity = Counter()
    for meta in blackboard.documents.values():
        for v in meta.get("violations", []):
            severity[v["severity"] or "Violation"] += 1

    validation_coverage = {
        "documents_validated": len(validated_docs),
        "validation_runs": len(validations) + len(violations),
        "conforming_runs": len(validations),
        "violating_runs": len(violations),
        "conformity_rate": round(len(validations) / max(len(validations) + len(violations), 1), 3),
        "violations_by_severity": dict(severity),
        "constraints_evaluated": (validations + violations)[0].payload.get("constraintsEvaluated")
        if (validations or violations) else None,
    }

    # ------------------------------------------------- qualité du raisonnement
    inferences = [e for e in events if e.type == TRIPLES_INFERRED]
    inconsistencies = [e for e in events if e.type == INCONSISTENCY_DETECTED]
    linkings = [e for e in events if e.type == LINKING_COMPLETED]
    inferred_total = sum(e.payload.get("inferredTriples", 0) for e in inferences)
    asserted_total = sum(e.payload.get("assertedTriples", 0) for e in inferences)

    reasoning_quality = {
        "documents_reasoned": len(inferences),
        "inferred_triples": inferred_total,
        "mean_inference_ratio": round(inferred_total / max(asserted_total, 1), 3),
        "inconsistencies_detected": len(inconsistencies),
        "sameas_links": sum(e.payload.get("sameAsLinks", 0) for e in linkings),
    }

    # ------------------------------------------------------------ vue pipeline
    outcomes = Counter(r["status"] for r in trace)
    pipeline = {
        "outcomes": dict(outcomes),
        "replanifications": sum(r["replans"] for r in trace),
        "semantic_events": len(events),
        "event_types": dict(Counter(e.type for e in events)),
        "blackboard": blackboard.stats(),
    }

    return {
        "throughput": throughput,
        "validation_coverage": validation_coverage,
        "reasoning_quality": reasoning_quality,
        "pipeline": pipeline,
    }
