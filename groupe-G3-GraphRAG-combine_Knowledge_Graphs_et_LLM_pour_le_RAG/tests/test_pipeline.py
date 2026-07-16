"""Tests for the pipeline orchestrator (graphrag_core.pipeline)."""

from unittest.mock import MagicMock
from graphrag_core.extractor import Triple
from graphrag_core.graph import build_knowledge_graph
from graphrag_core.pipeline import run, PipelineResult

_TRIPLES = [Triple("Alice", "WORKS_AT", "ACME"), Triple("Alice", "KNOWS", "Bob")]


def _kg():
    """Build a small test KnowledgeGraph.

    Returns:
        A KnowledgeGraph built from two triples involving Alice, ACME, and Bob.
    """
    return build_knowledge_graph(_TRIPLES, {})


def _llm(answer="Alice works at ACME."):
    """Create a mock LLMClient that returns a fixed answer.

    Args:
        answer: The string to return from ``complete``.

    Returns:
        A MagicMock whose ``complete`` method returns *answer*.
    """
    m = MagicMock()
    m.complete.return_value = answer
    return m


def test_run_returns_pipeline_result():
    """run() must return a PipelineResult with the LLM answer."""
    result = run("Where does Alice work?", _kg(), _llm())
    assert isinstance(result, PipelineResult)
    assert result.answer == "Alice works at ACME."


def test_run_subgraph_nodes_populated():
    """run() must populate subgraph_nodes and include Alice as a seed."""
    result = run("Where does Alice work?", _kg(), _llm())
    assert len(result.subgraph_nodes) > 0
    assert "Alice" in result.subgraph_nodes


def test_run_docs_used_matched():
    """run() must match docs whose text contains a subgraph node name."""
    docs = {"file.txt": "Alice is an employee at ACME corporation."}
    result = run("Where does Alice work?", _kg(), _llm(), docs_map=docs)
    assert any(d.filename == "file.txt" for d in result.docs_used)


def test_run_no_entity_match_uses_fallback():
    """run() must fall back to top-degree nodes when no seeds are detected."""
    result = run("What is the meaning of life?", _kg(), _llm("I don't know."))
    assert result.answer == "I don't know."
    assert len(result.subgraph_nodes) > 0  # fallback to top-degree nodes
