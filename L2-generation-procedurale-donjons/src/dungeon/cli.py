"""CLI `dungeon-gen` : generate / benchmark / report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .benchmark import SIZE_PRESETS, run_benchmark
from .generator import generate
from .metrics import evaluate
from .report import generate_report


def _cmd_generate(args: argparse.Namespace) -> None:
    result = generate(
        args.method,
        args.width,
        args.height,
        args.seed,
        n_rooms=args.rooms,
        symmetry=args.symmetry,
    )
    m = evaluate(result.grid)
    print(result.grid.to_ascii())
    print()
    print(f"methode={result.method} seed={result.seed} statut={result.solver_status} "
          f"temps={result.elapsed_s:.3f}s tentatives={result.n_attempts}")
    print(json.dumps(m.to_dict(), indent=2, ensure_ascii=False))
    if args.out:
        Path(args.out).write_text(json.dumps(result.grid.to_dict()), encoding="utf-8")


def _cmd_benchmark(args: argparse.Namespace) -> None:
    methods = args.methods.split(",")
    sizes = list(SIZE_PRESETS) if args.sizes == "all" else args.sizes.split(",")
    seeds = list(range(args.seeds))
    df = run_benchmark(methods, sizes, seeds, n_rooms=args.rooms)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"{len(df)} lignes ecrites dans {out_path}")


def _cmd_report(args: argparse.Namespace) -> None:
    df = pd.read_csv(args.inp)
    out_md = Path(args.out)
    generate_report(df, out_md, out_md.parent / "plots")
    print(f"rapport ecrit dans {out_md}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dungeon-gen")
    sub = parser.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("generate", help="generer un donjon")
    p_gen.add_argument("--method", choices=["cpsat", "wfc"], default="cpsat")
    p_gen.add_argument("--width", type=int, default=30)
    p_gen.add_argument("--height", type=int, default=22)
    p_gen.add_argument("--seed", type=int, default=0)
    p_gen.add_argument("--rooms", type=int, default=8)
    p_gen.add_argument("--symmetry", action="store_true")
    p_gen.add_argument("--out", type=str, default=None)
    p_gen.set_defaults(func=_cmd_generate)

    p_bench = sub.add_parser("benchmark", help="comparer CP-SAT et WFC")
    p_bench.add_argument("--methods", type=str, default="cpsat,wfc")
    p_bench.add_argument("--sizes", type=str, default="all")
    p_bench.add_argument("--seeds", type=int, default=10, help="nombre de graines 0..N-1")
    p_bench.add_argument("--rooms", type=int, default=8)
    p_bench.add_argument("--out", type=str, default="benchmarks/results/results.csv")
    p_bench.set_defaults(func=_cmd_benchmark)

    p_report = sub.add_parser("report", help="generer le rapport comparatif")
    p_report.add_argument("--in", dest="inp", type=str, default="benchmarks/results/results.csv")
    p_report.add_argument("--out", type=str, default="reports/report.md")
    p_report.set_defaults(func=_cmd_report)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
