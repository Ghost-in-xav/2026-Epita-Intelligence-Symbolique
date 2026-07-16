"""The generate -> verify -> re-prompt loop.

Step 1: the LLM proposes a candidate (strategy decides the prompt).
Step 2: the symbolic verifier accepts or rejects it.
Step 3: if rejected and attempts remain, re-prompt (the strategy may use the
        verifier's feedback). Stop on the first accepted answer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .llm.base import LLMProvider
from .parsing import extract_json
from .problems.base import Problem
from .records import Attempt
from .strategies import Strategy
from .verifier import verify


@dataclass
class PipelineRun:
    problem_id: str
    strategy: str
    provider: str
    model: str
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def solved(self) -> bool:
        return bool(self.attempts) and self.attempts[-1].result.ok

    @property
    def n_attempts(self) -> int:
        return len(self.attempts)

    @property
    def solved_at(self) -> int | None:
        """1-based attempt number that succeeded, or ``None``."""
        return self.n_attempts if self.solved else None

    @property
    def total_output_tokens(self) -> int:
        return sum(a.output_tokens or 0 for a in self.attempts)


def run_pipeline(
    problem: Problem,
    provider: LLMProvider,
    strategy: Strategy,
    *,
    max_attempts: int = 3,
    temperature: float = 0.0,
    on_attempt: Callable[["Attempt"], None] | None = None,
) -> PipelineRun:
    # Let offline/deterministic providers see the problem (ProblemAware).
    bind = getattr(provider, "bind", None)
    if callable(bind):
        bind(problem)

    run = PipelineRun(
        problem_id=problem.id,
        strategy=strategy.name,
        provider=provider.name,
        model=provider.model,
    )

    history: list[Attempt] = []
    for t in range(max_attempts):
        system, messages = strategy.build(problem, history)
        resp = provider.complete(messages, system=system, temperature=temperature)
        parsed = extract_json(resp.text)
        result = verify(problem, parsed)
        attempt = Attempt(
            index=t,
            response_text=resp.text,
            parsed=parsed,
            result=result,
            input_tokens=resp.input_tokens,
            output_tokens=resp.output_tokens,
        )
        history.append(attempt)
        run.attempts = history
        if on_attempt is not None:
            on_attempt(attempt)
        if result.ok:
            break

    return run
