from __future__ import annotations

import argparse
import sys

from botcheck import model_builder, properties
from botcheck.model_builder import _state
from botcheck.model_checker import CTLModelChecker, CheckResult
from botcheck.strategy import BotState

def _fmt_trace(keys) -> str:
    lines = []
    for i, k in enumerate(keys):
        st: BotState = _state(k)
        lines.append(f"      [{i}] {st}")
    return "\n".join(lines)

def verify_model(name: str, ks, quiet: bool = False) -> bool:
    print(f"\n=== Model checking CTL : {name} ===")
    print(f"    {ks}")
    mc = CTLModelChecker(ks)
    all_ok = True
    for pid, desc, formula in properties.ctl_properties():
        r: CheckResult = mc.check(formula)
        verdict = "OK   " if r.holds else "ECHEC"
        print(f"\n  [{verdict}] {pid}")
        if not quiet:
            print(f"          {desc}")
        print(f"          CTL : {formula}")
        if not r.holds:
            all_ok = False
            if r.counterexample:
                print(f"          Contre-exemple ({len(r.counterexample)} etats) :")
                print(_fmt_trace(r.counterexample))
        elif r.witness and not quiet:
            print(f"          Temoin ({len(r.witness)} etats) :")
            print(_fmt_trace(r.witness))
    return all_ok

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Model checking CTL du trading bot")
    ap.add_argument("--buggy", action="store_true",
                    help="verifier uniquement le modele fautif")
    ap.add_argument("--correct", action="store_true",
                    help="verifier uniquement le modele certifie")
    ap.add_argument("--quiet", action="store_true", help="sortie compacte")
    args = ap.parse_args(argv)

    print("#" * 70)
    print("#  S8 - Model checking CTL d'un bot de trading (Clarke-Emerson-Sistla)")
    print("#" * 70)

    ok = True
    if not args.buggy:
        ks = model_builder.build_kripke()
        ok_c = verify_model("MODELE CERTIFIE (deploiement autorise)", ks, args.quiet)
        ok = ok and ok_c
        print(f"\n  >>> Modele certifie : {'TOUTES les proprietes verifiees' if ok_c else 'VIOLATIONS detectees'}")

    if not args.correct:
        ksb = model_builder.build_kripke_buggy()
        ok_b = verify_model("MODELE FAUTIF (risk management desactive)", ksb, args.quiet)
        print(f"\n  >>> Modele fautif : {'aucune violation (?!)' if ok_b else 'violations attendues detectees (contre-exemples ci-dessus)'}")

    print("\n" + "#" * 70)
    if args.buggy:
        return 0
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
