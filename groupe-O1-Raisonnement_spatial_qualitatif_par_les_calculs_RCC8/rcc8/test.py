"""
Tests de validation du raisonneur RCC8.

Ce fichier peut etre execute directement avec:

    python3 -m rcc8.test

Les tests couvrent trois niveaux:
- les proprietes de base des relations RCC8;
- la forme et la coherence de la table de composition;
- le comportement du solveur PC-2 sur des reseaux coherents ou incoherents.
"""

from rcc8.composition_table import COMPOSE
from rcc8.rcc8solver import RCC8Solver
from rcc8.relations import ALL_RELATIONS, RCC8, inverse_relation, inverse_relations


def build_solver(vars=("A", "B", "C", "D")):
    """
    Construit un reseau RCC8 complet et non contraint.

    Au depart, chaque paire de regions peut avoir n'importe quelle relation
    RCC8. Les tests ajoutent ensuite des contraintes en remplacant certains
    ensembles par des singletons comme {"TPP"} ou {"EC"}.
    """
    R = {}

    for i in vars:
        for j in vars:
            if i == j:
                continue
            R[(i, j)] = set(ALL_RELATIONS)

    return RCC8Solver(list(vars), R)


def assert_inconsistent(solver):
    """
    Verifie qu'un reseau est detecte comme incoherent par la propagation.
    """
    try:
        solver.pc2()
        assert False, "Inconsistency not detected"
    except ValueError:
        pass


def test_inverse_relation():
    """
    Verifie les inverses RCC8.

    Les relations DC, EC, PO et EQ sont symetriques. TPP/NTPP ne le sont pas:
    leur inverse doit etre TPPI/NTPPI.
    """
    assert inverse_relation("TPP") == "TPPI"
    assert inverse_relation("TPPI") == "TPP"
    assert inverse_relation("NTPP") == "NTPPI"
    assert inverse_relation("NTPPI") == "NTPP"
    assert inverse_relation("EC") == "EC"
    assert inverse_relation(RCC8.TPP) == RCC8.TPPI

    print("TEST INVERSE OK")


def test_composition_table_shape():
    """
    Verifie que la table de composition est complete et fermee.

    Complete: chaque relation composee avec chaque relation a une entree.
    Fermee: le resultat contient uniquement des relations RCC8 valides.
    """
    for r in ALL_RELATIONS:
        assert set(COMPOSE[r]) == set(ALL_RELATIONS)
        for s in ALL_RELATIONS:
            assert COMPOSE[r][s]
            assert COMPOSE[r][s] <= set(ALL_RELATIONS)

    print("TEST TABLE COMPLETE OK")


def test_composition_table_converse_coherence():
    """
    Verifie une propriete algebrique importante de RCC8.

    Pour deux relations R et S:

        inverse(R o S) = inverse(S) o inverse(R)

    Ce test attrape les erreurs de table qui cassent la coherence entre
    R(A,B) et R(B,A).
    """
    for r in ALL_RELATIONS:
        for s in ALL_RELATIONS:
            left = inverse_relations(COMPOSE[r][s])
            right = COMPOSE[inverse_relation(s)][inverse_relation(r)]
            assert left == right, f"Converse mismatch for {r} o {s}"

    print("TEST TABLE INVERSE OK")


def test_converse_propagation_with_two_variables():
    """
    Verifie que le solveur synchronise automatiquement la relation inverse.

    Si A est une partie propre tangentielle de B, alors B doit etre l'inverse
    de cette relation par rapport a A.
    """
    solver = build_solver(("A", "B"))

    solver.R[("A", "B")] = {"TPP"}
    solver.pc2()

    assert solver.R[("A", "B")] == {"TPP"}
    assert solver.R[("B", "A")] == {"TPPI"}

    print("TEST CONVERSE TWO VARIABLES OK")


def test_symmetry():
    """
    Verifie qu'une relation symetrique reste identique dans les deux sens.
    """
    solver = build_solver(("A", "B"))

    solver.R[("A", "B")] = {"EC"}
    solver.pc2()

    assert solver.R[("A", "B")] == {"EC"}
    assert solver.R[("B", "A")] == {"EC"}

    print("TEST SYMETRIE OK")


def test_simple_coherent():
    """
    Teste une propagation simple sur trois regions.

    A TPP B signifie que A est dans B en touchant son bord.
    B EC C signifie que B touche C par le bord.
    Alors A et C ne peuvent etre que DC ou EC.
    """
    solver = build_solver(("A", "B", "C"))

    solver.R[("A", "B")] = {"TPP"}
    solver.R[("B", "C")] = {"EC"}
    solver.pc2()

    assert solver.R[("A", "C")] == {"DC", "EC"}
    assert solver.R[("C", "A")] == {"DC", "EC"}

    print("TEST SIMPLE OK")


def test_incoherent_direct():
    """
    Teste une contradiction visible apres composition.

    A TPP B et B TPP C impliquent que A est dans C. Imposer A DC C est donc
    impossible.
    """
    solver = build_solver(("A", "B", "C"))

    solver.R[("A", "B")] = {"TPP"}
    solver.R[("B", "C")] = {"TPP"}
    solver.R[("A", "C")] = {"DC"}

    assert_inconsistent(solver)

    print("TEST INCOHERENCE DIRECT OK")


def test_chain_propagation():
    """
    Verifie une deduction classique par chaine.

    Si A est dans B et B est dans C, alors A est dans C. La relation finale
    peut etre TPP ou NTPP selon le contact avec le bord de C.
    """
    solver = build_solver(("A", "B", "C"))

    solver.R[("A", "B")] = {"TPP"}
    solver.R[("B", "C")] = {"TPP"}
    solver.pc2()

    assert solver.R[("A", "C")] == {"TPP", "NTPP"}
    assert solver.R[("C", "A")] == {"TPPI", "NTPPI"}

    print("TEST CHAINE OK")


def test_hidden_inconsistency():
    """
    Teste une contradiction indirecte.

    A NTPP B et B NTPP C impliquent que A est strictement a l'interieur de C.
    La contrainte inverse C DC A rend donc le reseau incoherent.
    """
    solver = build_solver(("A", "B", "C"))

    solver.R[("A", "B")] = {"NTPP"}
    solver.R[("B", "C")] = {"NTPP"}
    solver.R[("C", "A")] = {"DC"}

    assert_inconsistent(solver)

    print("TEST HIDDEN INCONSISTENCY OK")


def test_complex_network():
    """
    Lance le solveur sur un petit reseau plus dense.

    Ici on ne cherche pas un resultat exact pour chaque paire: ce test sert a
    verifier que la propagation atteint un point fixe sans vider un domaine.
    """
    solver = build_solver(("A", "B", "C", "D"))

    solver.R[("A", "B")] = {"TPP"}
    solver.R[("B", "C")] = {"EC"}
    solver.R[("C", "D")] = {"PO"}
    solver.R[("A", "D")] = {
        "DC", "EC", "PO", "TPP", "NTPP", "TPPI", "NTPPI"
    }

    solver.pc2()

    for rels in solver.R.values():
        assert rels

    print("TEST COMPLEXE OK")


def run_all():
    """
    Execute tous les tests dans un ordre pedagogique.
    """
    test_inverse_relation()
    test_composition_table_shape()
    test_composition_table_converse_coherence()
    test_converse_propagation_with_two_variables()
    test_symmetry()
    test_simple_coherent()
    test_incoherent_direct()
    test_chain_propagation()
    test_hidden_inconsistency()
    test_complex_network()


if __name__ == "__main__":
    run_all()
