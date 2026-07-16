"""Tests for the multi-hop BFS retriever module."""

from graphrag_core.extractor import Triple
from graphrag_core.graph import build_knowledge_graph
from graphrag_core.retriever import detect_entities, extract_subgraph, subgraph_to_context

_TRIPLES = [
    Triple("Alice", "WORKS_AT", "ACME"),
    Triple("Alice", "KNOWS", "Bob"),
    Triple("Bob", "WORKS_AT", "TechCorp"),
    Triple("Bob", "LIVES_IN", "Paris"),
]


def _kg():
    """Build a small KnowledgeGraph fixture for testing.

    Returns:
        A KnowledgeGraph built from the module-level _TRIPLES list.
    """
    return build_knowledge_graph(_TRIPLES, {})


def test_detect_entities_case_insensitive():
    """detect_entities matches node names case-insensitively."""
    kg = _kg()
    assert "Alice" in detect_entities("Where does alice work?", kg)


def test_detect_entities_no_match():
    """detect_entities returns an empty list when no node name appears."""
    assert detect_entities("What is the weather?", _kg()) == []


def test_subgraph_one_hop_includes_neighbors():
    """extract_subgraph at 1 hop includes direct neighbours of seed nodes."""
    result = extract_subgraph(_kg(), ["Alice"], max_hops=1)
    assert "Alice" in result.nodes
    assert "ACME" in result.nodes


def test_subgraph_two_hops_reaches_paris():
    """extract_subgraph at 2 hops reaches nodes two steps away."""
    result = extract_subgraph(_kg(), ["Alice"], max_hops=2)
    assert "Paris" in result.nodes


def test_subgraph_trace_hop_numbers():
    """extract_subgraph populates trace with both hop 1 and hop 2 entries."""
    result = extract_subgraph(_kg(), ["Alice"], max_hops=2)
    hops = [s.hop for s in result.trace]
    assert 1 in hops
    assert 2 in hops


def test_subgraph_to_context_contains_relation():
    """subgraph_to_context produces lines in 'src --[rel]--> tgt' format."""
    result = extract_subgraph(_kg(), ["Alice"], max_hops=1)
    ctx = subgraph_to_context(result)
    assert "--[" in ctx
    assert "Alice" in ctx
