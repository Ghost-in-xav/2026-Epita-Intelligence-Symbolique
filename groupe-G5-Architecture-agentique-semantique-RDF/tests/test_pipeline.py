"""Tests d'intégration : orchestration complète plan/exécution/replanification."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from rdf_agents import Blackboard, Orchestrator
from rdf_agents.agents import (ExtractionAgent, LinkingAgent, QueryAgent,
                               ReasoningAgent, ValidationAgent)
from rdf_agents.metrics import evaluate

CORPUS = ROOT / "data/corpus"


@pytest.fixture
def system():
    bb = Blackboard()
    bb.load_ontology(ROOT / "ontology/catalog.ttl")
    agents = [
        ExtractionAgent(bb),
        ValidationAgent(bb, ROOT / "shapes/dataset_shapes.ttl"),
        ReasoningAgent(bb),
        QueryAgent(bb),
        LinkingAgent(bb, ROOT / "data/linked_data_cache"),
    ]
    return bb, Orchestrator(bb, ROOT / "planning/domain.pddl", agents), agents


def test_conforming_document_is_published(system):
    _, orch, _ = system
    record = orch.process_document(CORPUS / "doc1_datagouv_catalog.ttl",
                                   doc_id="doc1", needs_linking=True)
    assert record["status"] == "published"
    assert record["replans"] == 0
    assert "(link doc1)" in record["plan"]
    assert record["plan"][-1] == "(publish doc1)"


def test_violating_document_triggers_replanning_to_quarantine(system):
    _, orch, _ = system
    record = orch.process_document(CORPUS / "doc3_energie.jsonld", doc_id="doc3")
    assert record["status"] == "quarantined"
    assert record["replans"] == 1
    assert record["plan"][-1] == "(quarantine doc3)"
    assert "(reason doc3)" not in record["plan"]  # le raisonnement n'a pas lieu


def test_parse_failure_quarantined(system):
    _, orch, _ = system
    record = orch.process_document(CORPUS / "doc5_broken.ttl", doc_id="doc5")
    assert record["status"] == "quarantined"
    assert record["plan"] == ["(extract doc5)", "(quarantine doc5)"]


def test_inconsistency_quarantined_after_reasoning(system):
    _, orch, _ = system
    record = orch.process_document(CORPUS / "doc6_inconsistent.ttl", doc_id="doc6")
    assert record["status"] == "quarantined"
    assert "(reason doc6)" in record["plan"]


def test_revalidation_failure_after_inference_triggers_replanning(system):
    _, orch, _ = system
    record = orch.process_document(CORPUS / "doc7_postinference_violation.ttl",
                                   doc_id="doc7")
    # la validation initiale passe (le raisonnement a lieu) mais l'inférence
    # type `ghost` foaf:Person, cible de PersonShape qu'il viole -> la
    # re-validation échoue et déclenche la replanification vers la quarantaine.
    assert "(reason doc7)" in record["plan"]
    assert "(revalidate doc7)" in record["plan"]
    assert record["status"] == "quarantined"
    assert record["replans"] == 1
    assert record["plan"][-1] == "(quarantine doc7)"


def test_full_corpus_and_metrics(system):
    bb, orch, agents = system
    docs = [
        {"path": CORPUS / "doc1_datagouv_catalog.ttl", "id": "doc1", "needs_linking": True},
        {"path": CORPUS / "doc2_transport.rdf", "id": "doc2", "needs_linking": True},
        {"path": CORPUS / "doc3_energie.jsonld", "id": "doc3"},
        {"path": CORPUS / "doc4_dbpedia_excerpt.nt", "id": "doc4", "needs_linking": True},
        {"path": CORPUS / "doc5_broken.ttl", "id": "doc5"},
        {"path": CORPUS / "doc6_inconsistent.ttl", "id": "doc6"},
    ]
    trace = orch.process_corpus(docs)
    report = evaluate(bb, trace, agents)

    assert report["pipeline"]["outcomes"] == {"published": 3, "quarantined": 3}
    assert report["pipeline"]["replanifications"] == 3
    assert report["validation_coverage"]["violating_runs"] == 1
    # delta métier (hors bruit de clôture réflexif/axiomatique)
    assert report["reasoning_quality"]["inferred_triples"] > 20
    assert report["reasoning_quality"]["inconsistencies_detected"] == 1
    assert report["reasoning_quality"]["sameas_links"] >= 3
    assert report["throughput"]["documents"] == 6

    # requête fédérée inter-documents sur les connaissances publiées + inférées
    rows = list(bb.query("""
        PREFIX ex: <http://epita.fr/scia/2026/g5/catalog#>
        SELECT DISTINCT ?d WHERE { ?d a ex:GovDataset }"""))
    assert len(rows) >= 2  # doc1 (INSEE) et doc2 (IdF Mobilités), types inférés
