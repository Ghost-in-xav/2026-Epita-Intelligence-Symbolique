"""Tests unitaires des agents spécialisés."""

import sys
from pathlib import Path

import pytest
from rdflib import OWL

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from rdf_agents import Blackboard
from rdf_agents.agents import (ExtractionAgent, LinkingAgent, QueryAgent,
                               ReasoningAgent, ValidationAgent)
from rdf_agents.events import (EXTRACTION_COMPLETED, EXTRACTION_FAILED,
                               INCONSISTENCY_DETECTED, INDEXING_COMPLETED,
                               LINKING_COMPLETED, TRIPLES_INFERRED,
                               VALIDATION_SUCCEEDED, VIOLATION_DETECTED)

CORPUS = ROOT / "data/corpus"


@pytest.fixture
def blackboard():
    bb = Blackboard()
    bb.load_ontology(ROOT / "ontology/catalog.ttl")
    return bb


def _ingest(bb, filename, doc_id="t"):
    doc_uri = bb.register_document(doc_id, CORPUS / filename)
    event = ExtractionAgent(bb).perform("extract", doc_uri)
    return doc_uri, event


# ------------------------------------------------------------------ extraction
@pytest.mark.parametrize("filename,fmt", [
    ("doc1_datagouv_catalog.ttl", "turtle"),
    ("doc2_transport.rdf", "xml"),
    ("doc3_energie.jsonld", "json-ld"),
    ("doc4_dbpedia_excerpt.nt", "nt"),
])
def test_extraction_multiformat(blackboard, filename, fmt):
    doc_uri, event = _ingest(blackboard, filename)
    assert event.type == EXTRACTION_COMPLETED
    assert event.payload["format"] == fmt
    assert len(blackboard.doc_graph(doc_uri)) == event.payload["triples"] > 0


def test_extraction_failure_on_malformed(blackboard):
    _, event = _ingest(blackboard, "doc5_broken.ttl")
    assert event.type == EXTRACTION_FAILED


# ------------------------------------------------------------------ validation
def test_validation_conforming_document(blackboard):
    doc_uri, _ = _ingest(blackboard, "doc1_datagouv_catalog.ttl")
    agent = ValidationAgent(blackboard, ROOT / "shapes/dataset_shapes.ttl")
    event = agent.perform("validate", doc_uri)
    assert event.type == VALIDATION_SUCCEEDED
    # 9 property shapes + 1 contrainte SPARQL réellement évaluées
    assert event.payload["constraintsEvaluated"] == 10


def test_validation_detects_violations_and_persists_report(blackboard):
    doc_uri, _ = _ingest(blackboard, "doc3_energie.jsonld")
    agent = ValidationAgent(blackboard, ROOT / "shapes/dataset_shapes.ttl")
    event = agent.perform("validate", doc_uri)
    assert event.type == VIOLATION_DETECTED
    assert event.payload["violationCount"] >= 3  # titre manquant, dates, mbox...
    # le rapport SHACL est persisté dans le graphe partagé
    assert len(blackboard.reports_graph) > 0
    violations = blackboard.documents[doc_uri]["violations"]
    severities = {v["severity"] for v in violations}
    assert "Violation" in severities and "Warning" in severities
    messages = " ".join(v["message"] for v in violations)
    assert "modification" in messages  # contrainte SPARQL modified >= issued


# ------------------------------------------------------------------ raisonnement
def test_reasoning_infers_gov_dataset(blackboard):
    doc_uri, _ = _ingest(blackboard, "doc1_datagouv_catalog.ttl")
    event = ReasoningAgent(blackboard).perform("reason", doc_uri)
    assert event.type == TRIPLES_INFERRED
    assert event.payload["inferredTriples"] > 0
    combined = blackboard.combined_doc_graph(doc_uri)
    rows = list(combined.query("""
        PREFIX ex: <http://epita.fr/scia/2026/g5/catalog#>
        ASK { ?d a ex:GovDataset }"""))
    assert rows[0] is True  # inféré via publisher some PublicBody


def test_reasoning_detects_disjointness_inconsistency(blackboard):
    doc_uri, _ = _ingest(blackboard, "doc6_inconsistent.ttl")
    event = ReasoningAgent(blackboard).perform("reason", doc_uri)
    assert event.type == INCONSISTENCY_DETECTED
    assert "chimera" in event.payload["details"]


# ------------------------------------------------------------------ requêtage
def test_query_agent_partitions_by_class(blackboard):
    doc_uri, _ = _ingest(blackboard, "doc1_datagouv_catalog.ttl")
    ReasoningAgent(blackboard).perform("reason", doc_uri)
    event = QueryAgent(blackboard).perform("index", doc_uri)
    assert event.type == INDEXING_COMPLETED
    assert event.payload["partitions"] >= 2
    partitions = blackboard.documents[doc_uri]["partitions"]
    assert "datasets" in partitions and "organizations" in partitions


# ------------------------------------------------------------------ liage
def test_linking_agent_produces_sameas(blackboard):
    doc_uri, _ = _ingest(blackboard, "doc1_datagouv_catalog.ttl")
    agent = LinkingAgent(blackboard, ROOT / "data/linked_data_cache")
    event = agent.perform("link", doc_uri)
    assert event.type == LINKING_COMPLETED
    assert event.payload["sameAsLinks"] >= 1
    links = list(blackboard.links_graph.subject_objects(OWL.sameAs))
    assert any("dbpedia.org" in str(o) or "wikidata.org" in str(o)
               for _, o in links)


# ------------------------------------------------------------------ évènements RDF
def test_events_are_materialized_in_shared_graph(blackboard):
    _ingest(blackboard, "doc1_datagouv_catalog.ttl")
    rows = list(blackboard.events_graph.query("""
        PREFIX ag: <http://epita.fr/scia/2026/g5/agents#>
        SELECT ?e WHERE { ?e a ag:ExtractionCompleted ; ag:emittedBy ag:ExtractionAgent }"""))
    assert len(rows) == 1
