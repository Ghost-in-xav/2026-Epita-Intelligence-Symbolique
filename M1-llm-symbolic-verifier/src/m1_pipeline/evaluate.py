"""Evaluation harness: rejection rate, correction rate, error analysis, baselines.

It runs each strategy over the benchmark and reports the metrics named in the M1
subject, plus the two reference points it asks to compare against:
the LLM alone (zero-shot / few-shot, i.e. a single attempt) and the symbolic
solver alone (Z3, the oracle).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field

from .llm.base import LLMProvider
from .pipeline import run_pipeline
from .problems.base import Problem
from .strategies import get_strategy
from .verifier import Status, solve


@dataclass
class StrategyStats:
    strategy: str
    runs: int = 0
    solved: int = 0
    sat_runs: int = 0
    sat_solved: int = 0
    unsat_runs: int = 0
    unsat_correct: int = 0          # unsat problem correctly left unsolved
    total_attempts: int = 0
    rejected_attempts: int = 0
    attempts_to_solve: list[int] = field(default_factory=list)
    error_categories: Counter = field(default_factory=Counter)

    @property
    def solve_rate(self) -> float:
        return self.sat_solved / self.sat_runs if self.sat_runs else 0.0

    @property
    def rejection_rate(self) -> float:
        return self.rejected_attempts / self.total_attempts if self.total_attempts else 0.0

    @property
    def mean_attempts_to_solve(self) -> float:
        return sum(self.attempts_to_solve) / len(self.attempts_to_solve) if self.attempts_to_solve else 0.0

    def to_dict(self) -> dict:
        d = {k: v for k, v in asdict(self).items() if k != "error_categories"}
        d["error_categories"] = dict(self.error_categories)
        d["solve_rate"] = round(self.solve_rate, 3)
        d["rejection_rate"] = round(self.rejection_rate, 3)
        d["mean_attempts_to_solve"] = round(self.mean_attempts_to_solve, 2)
        return d


@dataclass
class BenchmarkReport:
    provider: str
    model: str
    max_attempts: int
    repeat: int
    strategies: dict[str, StrategyStats] = field(default_factory=dict)
    solver_only_solve_rate: float = 0.0   # over satisfiable problems
    per_domain_solve_rate: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "max_attempts": self.max_attempts,
            "repeat": self.repeat,
            "solver_only_solve_rate": round(self.solver_only_solve_rate, 3),
            "per_domain_solve_rate": {k: round(v, 3) for k, v in self.per_domain_solve_rate.items()},
            "strategies": {n: s.to_dict() for n, s in self.strategies.items()},
        }

    def to_markdown(self) -> str:
        lines = [
            f"# M1 benchmark — {self.provider} / {self.model}",
            "",
            f"- max attempts: {self.max_attempts}, repeats: {self.repeat}",
            f"- solver-only (Z3) solve rate on satisfiable problems: "
            f"{self.solver_only_solve_rate:.0%}",
            "",
            "## Strategies",
            "",
            "| strategy | solve rate | rejection rate | mean attempts→solve |",
            "|---|---|---|---|",
        ]
        for name, s in self.strategies.items():
            lines.append(
                f"| {name} | {s.solve_rate:.0%} | {s.rejection_rate:.0%} | "
                f"{s.mean_attempts_to_solve:.2f} |"
            )
        lines += ["", "## Error categories (rejected attempts)", ""]
        agg: Counter = Counter()
        for s in self.strategies.values():
            agg.update(s.error_categories)
        if agg:
            lines += ["| category | count |", "|---|---|"]
            for cat, n in agg.most_common():
                lines.append(f"| {cat} | {n} |")
        else:
            lines.append("_no rejected attempts_")
        lines += ["", "## Per-domain solve rate (best over strategies)", ""]
        lines += ["| domain | solve rate |", "|---|---|"]
        for dom, rate in sorted(self.per_domain_solve_rate.items()):
            lines.append(f"| {dom} | {rate:.0%} |")
        return "\n".join(lines)


def run_benchmark(
    provider: LLMProvider,
    problems: list[Problem],
    strategy_names: list[str],
    *,
    max_attempts: int = 3,
    repeat: int = 1,
    temperature: float = 0.0,
    on_run=None,
) -> BenchmarkReport:
    report = BenchmarkReport(
        provider=provider.name,
        model=provider.model,
        max_attempts=max_attempts,
        repeat=repeat,
    )

    # Solver-only baseline (oracle).
    sat_problems = [p for p in problems if p.satisfiable]
    solver_solved = sum(1 for p in sat_problems if solve(p) is not None)
    report.solver_only_solve_rate = solver_solved / len(sat_problems) if sat_problems else 0.0

    # Track best per-domain solve rate across strategies.
    domain_best: dict[str, float] = {}
    domain_runs: dict[str, dict[str, list[int]]] = {}  # domain -> strat -> [0/1]

    for sname in strategy_names:
        strategy = get_strategy(sname)
        stats = StrategyStats(strategy=sname)
        for problem in problems:
            for _ in range(repeat):
                run = run_pipeline(
                    problem, provider, strategy,
                    max_attempts=max_attempts, temperature=temperature,
                )
                if on_run is not None:
                    on_run(run)
                stats.runs += 1
                stats.total_attempts += run.n_attempts
                for att in run.attempts:
                    if not att.result.ok:
                        stats.rejected_attempts += 1
                        stats.error_categories[att.result.error_category] += 1
                if problem.satisfiable:
                    stats.sat_runs += 1
                    if run.solved:
                        stats.sat_solved += 1
                        stats.solved += 1
                        stats.attempts_to_solve.append(run.n_attempts)
                    domain_runs.setdefault(problem.domain, {}).setdefault(sname, []).append(
                        1 if run.solved else 0
                    )
                else:
                    stats.unsat_runs += 1
                    if not run.solved:  # correctly never accepted a bogus answer
                        stats.unsat_correct += 1
        report.strategies[sname] = stats

    for domain, by_strat in domain_runs.items():
        best = 0.0
        for runs in by_strat.values():
            rate = sum(runs) / len(runs) if runs else 0.0
            best = max(best, rate)
        domain_best[domain] = best
    report.per_domain_solve_rate = domain_best

    return report
