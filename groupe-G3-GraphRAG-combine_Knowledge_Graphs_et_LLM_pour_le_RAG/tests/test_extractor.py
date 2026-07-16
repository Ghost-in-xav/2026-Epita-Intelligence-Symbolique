from unittest.mock import MagicMock
from graphrag_core.extractor import extract_triples, chunk_text, Triple


def _mock_llm(response: str):
    """Create a mock LLMClient whose complete() returns a fixed response.

    Args:
        response: The string that llm.complete() will return.

    Returns:
        A MagicMock configured to return response from .complete().
    """
    llm = MagicMock()
    llm.complete.return_value = response
    return llm


def test_extract_triples_basic():
    """A single valid triple is parsed and returned."""
    llm = _mock_llm('[{"subject": "Alice", "relation": "WORKS_AT", "object": "ACME"}]')
    triples = extract_triples("Alice works at ACME.", llm)
    assert len(triples) == 1
    assert triples[0] == Triple("Alice", "WORKS_AT", "ACME")


def test_extract_triples_deduplication():
    """Duplicate triples in the LLM output are collapsed to one."""
    llm = _mock_llm('[{"subject":"A","relation":"R","object":"B"},{"subject":"A","relation":"R","object":"B"}]')
    triples = extract_triples("text", llm)
    assert len(triples) == 1


def test_extract_triples_invalid_json_returns_empty():
    """Non-JSON LLM output produces an empty list."""
    llm = _mock_llm("Sorry, I cannot extract anything.")
    assert extract_triples("text", llm) == []


def test_extract_triples_missing_field_skipped():
    """Triples missing the 'object' field are silently skipped."""
    llm = _mock_llm('[{"subject": "A", "relation": "R"}]')
    assert extract_triples("text", llm) == []


def test_chunk_text_short_stays_single():
    """Text shorter than chunk_size is returned as a single-element list."""
    assert chunk_text("hello", chunk_size=2000) == ["hello"]


def test_chunk_text_long_produces_multiple():
    """Text longer than chunk_size is split into multiple overlapping chunks."""
    chunks = chunk_text("x" * 5000, chunk_size=2000, overlap=200)
    assert len(chunks) > 1
    assert all(len(c) <= 2000 for c in chunks)
