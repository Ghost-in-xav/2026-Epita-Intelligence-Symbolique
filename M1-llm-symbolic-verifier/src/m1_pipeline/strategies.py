"""Re-prompting strategies.

A strategy decides what to send to the LLM at each attempt, given the history of
previous (rejected) attempts. The subject asks for at least three; we ship five:

* ``direct``         — single straight-to-JSON prompt (the control).
* ``chain_of_thought`` — reason step by step, then answer.
* ``reformulation``  — on retry, restate the constraints as an explicit checklist.
* ``decomposition``  — solve variable by variable, deducing values incrementally.
* ``counterexample`` — feed the verifier's violated constraints back (CEGIS-style).

The last one closes the neuro-symbolic loop: the symbolic verifier's rejection is
turned into a corrective signal for the neural generator.
"""
from __future__ import annotations

from typing import Protocol

from .llm.base import Message
from .problems.base import Problem
from .records import Attempt

_JSON_ONLY = (
    "Output ONLY a single JSON object and nothing else — no prose, no markdown, "
    "no code fences."
)


def _format_block(problem: Problem) -> str:
    return (
        f"{problem.statement}\n\n"
        f"Expected answer format:\n{problem.answer_format}"
    )


def _violations(att: Attempt) -> str:
    r = att.result
    if r.violated:
        lines = "\n".join(f"  - {v}" for v in r.violated)
        return f"The previous answer {att.parsed} was rejected. Violated constraints:\n{lines}"
    return f"The previous answer was rejected ({r.error_category}): {r.message}"


class Strategy(Protocol):
    name: str

    def build(self, problem: Problem, history: list[Attempt]) -> tuple[str, list[Message]]:
        ...


class DirectStrategy:
    name = "direct"

    def build(self, problem, history):
        system = f"You are a careful problem solver. {_JSON_ONLY}"
        user = _format_block(problem) + "\n\nRespond with only the JSON object."
        return system, [Message("user", user)]


class FewShotStrategy:
    """Direct prompt enriched with the problem's worked example (baseline)."""

    name = "few_shot"

    def build(self, problem, history):
        system = f"You are a careful problem solver. {_JSON_ONLY}"
        user = ""
        if problem.few_shot:
            user += f"Worked example / hint:\n{problem.few_shot}\n\n"
        user += _format_block(problem) + "\n\nRespond with only the JSON object."
        return system, [Message("user", user)]


class ChainOfThoughtStrategy:
    name = "chain_of_thought"

    def build(self, problem, history):
        system = "You are a careful reasoner who solves constraint problems step by step."
        user = (
            _format_block(problem)
            + "\n\nReason step by step about each clue. Then, on the final line, "
            "write 'ANSWER:' followed by the single JSON object."
        )
        return system, [Message("user", user)]


class ReformulationStrategy:
    name = "reformulation"

    def build(self, problem, history):
        system = f"You are a careful problem solver. {_JSON_ONLY}"
        user = _format_block(problem)
        if history:
            user += (
                "\n\nThe earlier attempt was wrong. Re-read the problem carefully. "
                "List each constraint as an explicit checklist item, then choose "
                "values that satisfy EVERY item at once before answering."
            )
        user += "\n\nRespond with only the JSON object."
        return system, [Message("user", user)]


class DecompositionStrategy:
    name = "decomposition"

    def build(self, problem, history):
        system = "You are a careful reasoner who decomposes problems into sub-steps."
        user = (
            _format_block(problem)
            + "\n\nSolve it incrementally: handle the constraints one at a time, "
            "deducing or narrowing the value of each variable, and check "
            "consistency as you go. Then on the final line write 'ANSWER:' "
            "followed by the single JSON object."
        )
        return system, [Message("user", user)]


class CounterexampleStrategy:
    """CEGIS-style: replay the conversation and feed back violated constraints."""

    name = "counterexample"

    def build(self, problem, history):
        system = f"You are a careful problem solver. {_JSON_ONLY}"
        messages: list[Message] = [
            Message("user", _format_block(problem) + "\n\nRespond with only the JSON object.")
        ]
        for att in history:
            messages.append(Message("assistant", att.response_text))
            messages.append(
                Message(
                    "user",
                    _violations(att)
                    + "\n\nFix the assignment so all constraints hold. "
                    "Respond with only the corrected JSON object.",
                )
            )
        return system, messages


_STRATEGIES: dict[str, Strategy] = {
    s.name: s
    for s in (
        DirectStrategy(),
        FewShotStrategy(),
        ChainOfThoughtStrategy(),
        ReformulationStrategy(),
        DecompositionStrategy(),
        CounterexampleStrategy(),
    )
}


def get_strategy(name: str) -> Strategy:
    if name not in _STRATEGIES:
        raise KeyError(f"unknown strategy {name!r}; known: {list(_STRATEGIES)}")
    return _STRATEGIES[name]


def strategy_names() -> list[str]:
    return list(_STRATEGIES)
