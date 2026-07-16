from __future__ import annotations

import argparse
import sys
from collections import Counter

from botcheck.backtest import BacktestConfig, run_backtest, synthetic_prices

def load_csv(path: str):
    import csv
    prices = []
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row:
                continue
            try:
                prices.append(float(row[-1]))
            except ValueError:
                continue
    return prices

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Backtest + runtime CTL monitoring")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--csv", type=str, default=None)
    ap.add_argument("--stress", action="store_true",
                    help="marche tres volatil (sigma x3, chocs frequents)")
    args = ap.parse_args(argv)

    if args.csv:
        prices = load_csv(args.csv)
        src = f"CSV {args.csv}"
    elif args.stress:
        prices = synthetic_prices(seed=args.seed, sigma=0.035, shock_prob=0.04)
        src = f"synthetique STRESS (seed={args.seed})"
    else:
        prices = synthetic_prices(seed=args.seed)
        src = f"synthetique (seed={args.seed})"

    print("#" * 70)
    print(f"#  Backtest bot certifie + runtime CTL monitoring")
    print(f"#  Source de prix : {src} | {len(prices)} barres")
    print("#" * 70)

    res = run_backtest(prices, BacktestConfig())
    print("\n" + res.summary())

    modes = Counter(s.mode for s in res.states)
    print("\n  Repartition des modes :")
    for m, c in modes.most_common():
        print(f"    {m:16} {c:5}  ({100*c/len(res.states):.1f}%)")

    max_lev = max(s.leverage for s in res.states)
    max_dd_bucket = max(s.drawdown for s in res.states)
    print(f"\n  Levier max observe        : {max_lev}x  (borne prouvee : 2x)")
    print(f"  Bucket drawdown max       : {max_dd_bucket}  (3 = critique)")
    print(f"  Invariants CTL respectes  : {'OUI' if res.monitor.clean else 'NON'}")
    print(f"  Gaps modele/reel detectes : {len(res.monitor.gaps)}")
    print("#" * 70)
    return 0 if res.monitor.clean else 1

if __name__ == "__main__":
    sys.exit(main())
