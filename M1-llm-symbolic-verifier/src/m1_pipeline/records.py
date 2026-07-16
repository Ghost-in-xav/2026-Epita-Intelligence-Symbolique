"""Shared run records (kept separate to avoid a pipeline<->strategy import cycle)."""
from __future__ import annotations

from dataclasses import dataclass

from .verifier import VerificationResult


@dataclass
class Attempt:
    index: int                 # 0-based attempt number
    response_text: str         # raw LLM output
    parsed: dict | None        # extracted JSON answer (or None)
    result: VerificationResult
    input_tokens: int | None = None
    output_tokens: int | None = None
