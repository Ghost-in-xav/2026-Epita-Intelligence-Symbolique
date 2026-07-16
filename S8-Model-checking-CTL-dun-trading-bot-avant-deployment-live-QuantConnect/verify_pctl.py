from __future__ import annotations

import argparse
import sys

from botcheck import model_builder, pctl, properties

def run_queries(mdp, label: str) -> None:
    print(f"\n=== PCTL : {label} ===")
    print(f"    {mdp}")
    for q in properties.pctl_queries():
        if q["kind"] == "G_not":
            r = pctl.prob_eventually(mdp, q["ap"], maximize=True)
            res = pctl.PCTLResult(query=f"P=? [ G !{q['ap']} ]",
                                  prob_initial=1.0 - r.prob_initial)
            pctl.check_threshold(res, q["op"], q["threshold"])
        else:
            res = pctl.prob_eventually(mdp, q["ap"], maximize=q["maximize"])
            pctl.check_threshold(res, q["op"], q["threshold"])
        print(f"\n  {q['id']}")
        print(f"      {q['desc']}")
        print(f"      {res}")

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Model checking PCTL (MDP) du bot")
    ap.add_argument("--p-adverse", type=float, default=0.30,
                    help="proba d'un mouvement de marche adverse en position")
    args = ap.parse_args(argv)

    print("#" * 70)
    print("#  S8 - Extension : model checking PROBABILISTE PCTL (Storm/PRISM)")
    print(f"#  p_adverse = {args.p_adverse}")
    print("#" * 70)

    mdp_ok = model_builder.build_mdp(p_adverse=args.p_adverse, buggy=False)
    run_queries(mdp_ok, "MODELE CERTIFIE")

    mdp_bug = model_builder.build_mdp(p_adverse=args.p_adverse, buggy=True)
    run_queries(mdp_bug, "MODELE FAUTIF (risk management desactive)")

    r_ok = pctl.prob_eventually(mdp_ok, "margin_call", maximize=True)
    r_bug = pctl.prob_eventually(mdp_bug, "margin_call", maximize=True)
    print("\n" + "-" * 70)
    print("  COMPARAISON  P[ G !margin_call ] :")
    print(f"    certifie : {1 - r_ok.prob_initial:.6f}   (certitude totale, cf. CTL/NuSMV)")
    print(f"    fautif   : {1 - r_bug.prob_initial:.6f}   (risque quantifie par Storm/PRISM)")
    print("-" * 70 + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
