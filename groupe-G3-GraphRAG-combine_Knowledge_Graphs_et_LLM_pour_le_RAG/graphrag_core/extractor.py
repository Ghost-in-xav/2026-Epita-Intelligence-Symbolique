import json
import re
from dataclasses import dataclass
from typing import List

from .llm import LLMClient


@dataclass(frozen=True)
class Triple:
    """An immutable subject-relation-object knowledge graph triple.

    Attributes:
        subject: The entity that is the source of the relation.
        relation: The relation label, expected in UPPER_SNAKE_CASE.
        object: The entity that is the target of the relation.
    """

    subject: str
    relation: str
    object: str


_PROMPT = """Extract all entities and relations from the text as a JSON array of triples.
Each triple: {{"subject": "...", "relation": "UPPER_SNAKE_CASE", "object": "..."}}.
Output ONLY valid JSON. No explanation.

Text:
{text}"""


def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    """Split a text into overlapping chunks of at most chunk_size characters.

    If the text is shorter than or equal to chunk_size it is returned as-is in
    a single-element list.  Otherwise the text is sliced with a sliding window
    of size chunk_size and a step of (chunk_size - overlap), so consecutive
    chunks share overlap characters.

    Args:
        text: The input text to split.
        chunk_size: Maximum number of characters per chunk.
        overlap: Number of characters shared between consecutive chunks.

    Returns:
        A list of string chunks, each at most chunk_size characters long.
    """
    if len(text) <= chunk_size:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + chunk_size])
        start += chunk_size - overlap
    return chunks


def extract_triples(text: str, llm: LLMClient) -> List[Triple]:
    """Extract knowledge graph triples from text using an LLM.

    The text is split into overlapping chunks via chunk_text.  Each chunk is
    sent to the LLM with a structured prompt that requests a JSON array of
    triples.  The raw response is searched for the first JSON array, which is
    then parsed.  Items that are missing any of the required fields
    (``subject``, ``relation``, ``object``) are silently skipped.  Duplicate
    triples across all chunks are collapsed so that each unique triple appears
    only once in the returned list.

    Args:
        text: The input text to extract triples from.
        llm: An LLMClient instance used to call the model.

    Returns:
        A deduplicated list of Triple instances extracted from the text,
        preserving first-occurrence order.
    """
    seen: set = set()
    result: List[Triple] = []
    for chunk in chunk_text(text):
        raw = llm.complete(_PROMPT.format(text=chunk))
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if not m:
            continue
        try:
            items = json.loads(m.group())
        except json.JSONDecodeError:
            continue
        for item in items:
            if not all(k in item for k in ("subject", "relation", "object")):
                continue
            t = Triple(
                item["subject"].strip(),
                item["relation"].strip(),
                item["object"].strip(),
            )
            if t not in seen:
                seen.add(t)
                result.append(t)
    return result
