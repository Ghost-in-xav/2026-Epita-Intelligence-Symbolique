"""M1 — Pipeline LLM + verificateur symbolique pour la generation fiable."""

from .pipeline import PipelineRun, run_pipeline
from .verifier import VerificationResult, solve, verify

__all__ = ["PipelineRun", "run_pipeline", "VerificationResult", "verify", "solve"]
__version__ = "0.1.0"
