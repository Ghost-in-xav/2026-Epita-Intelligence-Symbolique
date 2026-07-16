"""Command-line interface.

    m1 list                 list benchmark problems
    m1 providers            list provider presets and strategies
    m1 solve <problem>      run the pipeline on one problem (full trace)
    m1 bench                run the full benchmark and print/save a report

The LLM backend is chosen with --provider (preset name, an http(s):// base URL,
or 'mock' for the offline Z3 oracle) and swapped freely without touching code.
"""
from __future__ import annotations

import argparse
import json
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from .evaluate import run_benchmark
from .llm import LLMError, make_provider
from .llm.presets import list_presets
from .pipeline import run_pipeline
from .problems import ALL_PROBLEMS, get_problem
from .strategies import get_strategy, strategy_names

console = Console()


def _add_provider_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--provider", default="anthropic",
                   help="preset (anthropic, openai, ollama, openrouter, local), "
                        "an http(s):// base URL, or 'mock'")
    p.add_argument("--model", default=None, help="model id (overrides preset default)")
    p.add_argument("--base-url", default=None, help="override the endpoint base URL")
    p.add_argument("--api-key-env", default=None, help="env var holding the API key")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--mock-fail-first", type=int, default=0,
                   help="mock provider: number of initial attempts to fail on purpose")


def _build_provider(args):
    return make_provider(
        args.provider,
        model=args.model,
        base_url=getattr(args, "base_url", None),
        api_key_env=getattr(args, "api_key_env", None),
        mock_fail_first=getattr(args, "mock_fail_first", 0),
    )


def cmd_list(_args):
    table = Table(title="Benchmark problems")
    table.add_column("id"); table.add_column("domain"); table.add_column("sat")
    table.add_column("title")
    for p in ALL_PROBLEMS:
        table.add_row(p.id, p.domain, "yes" if p.satisfiable else "NO", p.title)
    console.print(table)


def cmd_providers(_args):
    pt = Table(title="Provider presets  (swap with --provider <name>)")
    pt.add_column("name"); pt.add_column("base_url"); pt.add_column("api_key_env")
    pt.add_column("default_model")
    pt.add_row("mock", "(offline Z3 oracle)", "-", "oracle-z3")
    for pr in list_presets():
        pt.add_row(pr.name, pr.base_url or "(SDK default)", pr.api_key_env or "-", pr.default_model)
    console.print(pt)
    console.print(f"\nStrategies: [bold]{', '.join(strategy_names())}[/bold]")


def _render_run(run):
    head = "[green]SOLVED[/green]" if run.solved else "[red]UNSOLVED[/red]"
    console.print(f"\n{head}  problem=[bold]{run.problem_id}[/bold] "
                  f"strategy={run.strategy} provider={run.provider}/{run.model} "
                  f"attempts={run.n_attempts}")
    for att in run.attempts:
        r = att.result
        tag = "[green]accepted[/green]" if r.ok else f"[red]{r.error_category}[/red]"
        console.print(f"  attempt {att.index + 1}: {tag}  answer={att.parsed}")
        if r.violated:
            for v in r.violated:
                console.print(f"      violated: {v}")
        elif not r.ok and r.message:
            console.print(f"      {r.message}")


def cmd_solve(args):
    problem = get_problem(args.problem)
    strategy = get_strategy(args.strategy)
    provider = _build_provider(args)
    try:
        run = run_pipeline(problem, provider, strategy,
                           max_attempts=args.max_attempts, temperature=args.temperature)
    except LLMError as exc:
        console.print(f"[red]LLM error:[/red] {exc}")
        sys.exit(1)
    _render_run(run)


def cmd_bench(args):
    provider = _build_provider(args)
    strategies = args.strategies or strategy_names()
    problems = ALL_PROBLEMS if not args.problems else [get_problem(p) for p in args.problems]
    try:
        report = run_benchmark(
            provider, problems, strategies,
            max_attempts=args.max_attempts, repeat=args.repeat,
            temperature=args.temperature,
            on_run=_render_run if args.verbose else None,
        )
    except LLMError as exc:
        console.print(f"[red]LLM error:[/red] {exc}")
        sys.exit(1)

    console.print()
    console.print(report.to_markdown())
    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(report.to_dict(), fh, indent=2)
        console.print(f"\n[dim]JSON report written to {args.json_out}[/dim]")
    if args.md_out:
        with open(args.md_out, "w") as fh:
            fh.write(report.to_markdown())
        console.print(f"[dim]Markdown report written to {args.md_out}[/dim]")


def cmd_serve(args):
    from .web import serve  # lazy import so `m1 list` works without web deps
    console.print(f"[bold]Live demo UI[/bold] → http://{args.host}:{args.port}")
    serve(host=args.host, port=args.port)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="m1", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list benchmark problems").set_defaults(func=cmd_list)
    sub.add_parser("providers", help="list providers and strategies").set_defaults(func=cmd_providers)

    sp = sub.add_parser("solve", help="run the pipeline on one problem")
    sp.add_argument("problem", help="problem id (see `m1 list`)")
    sp.add_argument("--strategy", default="counterexample", choices=strategy_names())
    sp.add_argument("--max-attempts", type=int, default=3)
    _add_provider_args(sp)
    sp.set_defaults(func=cmd_solve)

    bp = sub.add_parser("bench", help="run the benchmark")
    bp.add_argument("--strategies", nargs="*", choices=strategy_names(), default=None)
    bp.add_argument("--problems", nargs="*", default=None)
    bp.add_argument("--max-attempts", type=int, default=3)
    bp.add_argument("--repeat", type=int, default=1)
    bp.add_argument("--json-out", default=None)
    bp.add_argument("--md-out", default=None)
    bp.add_argument("--verbose", action="store_true", help="print each run trace")
    _add_provider_args(bp)
    bp.set_defaults(func=cmd_bench)

    srv = sub.add_parser("serve", help="launch the live-demo web UI")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8000)
    srv.set_defaults(func=cmd_serve)
    return parser


def main(argv: list[str] | None = None) -> None:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
