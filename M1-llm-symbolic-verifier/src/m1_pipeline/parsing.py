"""Extract the JSON answer object from a raw LLM completion.

LLMs wrap answers in prose, code fences or an ``ANSWER:`` prefix, so we try a few
extraction strategies and keep the last valid JSON object (the final answer is
usually last).
"""
from __future__ import annotations

import json
import re


def _balanced_objects(text: str) -> list[str]:
    """Return every top-level ``{...}`` substring with balanced braces."""
    out: list[str] = []
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    out.append(text[start : i + 1])
    return out


def _try_load(candidate: str):
    try:
        return json.loads(candidate)
    except (ValueError, TypeError):
        return None


def extract_json(text: str | None) -> dict | None:
    """Best-effort extraction of a JSON object from ``text``; ``None`` on failure."""
    if not text:
        return None

    candidates: list[str] = []
    candidates += re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    m = re.search(r"ANSWER:\s*(\{.*\})", text, re.DOTALL)
    if m:
        candidates.append(m.group(1))
    candidates += _balanced_objects(text)

    for candidate in reversed(candidates):
        obj = _try_load(candidate)
        if isinstance(obj, dict):
            return obj
    return None
