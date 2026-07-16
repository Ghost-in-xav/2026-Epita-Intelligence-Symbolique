#!/usr/bin/env python3
"""Démonstration de bout en bout de l'architecture agentique sémantique (G5).

Exécute le pipeline multi-agents sur le corpus hétérogène, affiche les plans
PDDL calculés, les évènements sémantiques, quelques requêtes SPARQL fédérées
et les métriques d'évaluation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from rdflib import Graph

from rdf_agents import Blackboard, Orchestrator
from rdf_agents.agents import (ExtractionAgent, LinkingAgent, QueryAgent,
                               ReasoningAgent, ValidationAgent)
from rdf_agents.metrics import evaluate

CORPUS = [
    {"path": ROOT / "data/corpus/doc1_datagouv_catalog.ttl", "id": "doc1", "needs_linking": True},
    {"path": ROOT / "data/corpus/doc2_transport.rdf",        "id": "doc2", "needs_linking": True},
    {"path": ROOT / "data/corpus/doc3_energie.jsonld",       "id": "doc3"},
    {"path": ROOT / "data/corpus/doc4_dbpedia_excerpt.nt",   "id": "doc4", "needs_linking": True},
    {"path": ROOT / "data/corpus/doc5_broken.ttl",           "id": "doc5"},
    {"path": ROOT / "data/corpus/doc6_inconsistent.ttl",     "id": "doc6"},
]


def build_system() -> tuple:
    blackboard = Blackboard()
    blackboard.load_ontology(ROOT / "ontology/catalog.ttl")
    agents = [
        ExtractionAgent(blackboard),
        ValidationAgent(blackboard, ROOT / "shapes/dataset_shapes.ttl"),
        ReasoningAgent(blackboard),
        QueryAgent(blackboard),
        LinkingAgent(blackboard, ROOT / "data/linked_data_cache"),
    ]
    orchestrator = Orchestrator(blackboard, ROOT / "planning/domain.pddl", agents)
    return blackboard, orchestrator, agents


def main() -> None:
    blackboard, orchestrator, agents = build_system()

    print("=" * 76)
    print("  G5 — Architecture agentique sémantique pour documents RDF")
    print("=" * 76)

    for doc in CORPUS:
        record = orchestrator.process_document(Path(doc["path"]), doc_id=doc["id"],
                                               needs_linking=doc.get("needs_linking", False))
        print(f"\n▶ {record['doc_id']}  [{Path(doc['path']).name}]  →  {record['status'].upper()}"
              f"  ({record['triples']} triplets, {record['inferred']} inférés,"
              f" {record['replans']} replanification(s))")
        print("  plan exécuté :", " ; ".join(record["plan"]))

    # ------------------------------------------------- évènements sémantiques
    print("\n" + "-" * 76)
    print("Journal des évènements sémantiques (protocole inter-agents) :")
    for event in blackboard.bus.log:
        print("  •", event)

    # ------------------------------------------------ requêtes inter-graphes
    print("\n" + "-" * 76)
    print("Requête SPARQL : type ex:GovDataset INFÉRÉ (asserté par aucun document)")
    # Le typage ex:GovDataset ne provient que de la restriction someValuesFrom de
    # l'ontologie : on le lit donc UNIQUEMENT dans les graphes inférés, puis on
    # récupère les titres dans l'union des connaissances.
    inferred_union = Graph()
    for ctx in blackboard.dataset.graphs():
        if str(ctx.identifier).startswith("urn:graph:inferred:"):
            inferred_union += ctx
    gov = {row.dataset for row in inferred_union.query(
        "PREFIX ex: <http://epita.fr/scia/2026/g5/catalog#> "
        "SELECT DISTINCT ?dataset WHERE { ?dataset a ex:GovDataset }")}
    titles = {row.d: row.t for row in blackboard.query(
        "PREFIX dct: <http://purl.org/dc/terms/> "
        "SELECT ?d ?t WHERE { ?d dct:title ?t }")}
    for ds in sorted(gov, key=str):
        print(f"  ex:GovDataset ⊢ {ds}  ({titles.get(ds)})")

    print("\nRequête SPARQL sur le journal d'évènements (auditabilité) :")
    q2 = """
    PREFIX ag: <http://epita.fr/scia/2026/g5/agents#>
    SELECT ?type (COUNT(?e) AS ?n) WHERE {
        ?e a ?type ; ag:emittedBy ?agent .
        FILTER(STRSTARTS(STR(?type), STR(ag:)))
    } GROUP BY ?type ORDER BY DESC(?n)"""
    for row in blackboard.events_graph.query(q2):
        print(f"  {str(row.type).split('#')[-1]:<24} × {row.n}")

    print("\nAlignements Linked Data (owl:sameAs) :")
    for s, p, o in blackboard.links_graph:
        if "dbpedia" in str(o) or "wikidata" in str(o):
            print(f"  {s}\n    owl:sameAs {o}")

    # -------------------------------------------------------------- métriques
    print("\n" + "=" * 76)
    print("Évaluation (débit / couverture de validation / qualité du raisonnement)")
    report = evaluate(blackboard, orchestrator.trace, agents)
    print(json.dumps(report, indent=2, ensure_ascii=False))

    out = ROOT / "docs" / "evaluation_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nRapport sauvegardé : {out}")


if __name__ == "__main__":
    main()
