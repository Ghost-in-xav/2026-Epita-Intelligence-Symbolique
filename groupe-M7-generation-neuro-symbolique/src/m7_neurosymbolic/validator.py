"""Contraintes dures du plan de cours : verification, faisabilite, resolution."""

from __future__ import annotations

from ortools.sat.python import cp_model

from .schema import (
    PlanCandidate,
    Session,
    Syllabus,
    ValidationResult,
    Violation,
    ViolationKind,
)


class Validator:
    def __init__(self, syllabus: Syllabus) -> None:
        self.syllabus = syllabus

    def validate(self, plan: PlanCandidate) -> ValidationResult:
        """Verifie un plan complet. Les explications repartent telles quelles dans le prompt."""
        violations = [
            *self._unknown_objectives(plan),
            *self._coverage(plan),
            *self._prerequisites(plan),
            *self._overlap(plan),
            *self._duration(plan),
        ]
        return ValidationResult(is_valid=not violations, violations=violations)

    def _unknown_objectives(self, plan: PlanCandidate) -> list[Violation]:
        known = self.syllabus.objective_ids
        return [
            Violation(
                kind=ViolationKind.UNKNOWN_OBJECTIVE,
                explanation=(
                    f"La session '{s.title}' reference l'objectif '{oid}', absent du syllabus. "
                    f"Objectifs autorises : {sorted(known)}."
                ),
                involved=(oid,),
            )
            for s in plan.sessions
            for oid in s.objectives
            if oid not in known
        ]

    def _coverage(self, plan: PlanCandidate) -> list[Violation]:
        covered = {o for s in plan.sessions for o in s.objectives}
        missing = sorted(self.syllabus.objective_ids - covered)
        if not missing:
            return []
        return [
            Violation(
                kind=ViolationKind.COVERAGE,
                explanation=(
                    f"Objectifs jamais couverts : {missing}. "
                    f"Chacun doit apparaitre dans au moins une session."
                ),
                involved=tuple(missing),
            )
        ]

    def _first_slot(self, plan: PlanCandidate) -> dict[str, int]:
        first: dict[str, int] = {}
        for s in plan.sessions:
            for oid in s.objectives:
                first[oid] = min(first.get(oid, s.start_slot), s.start_slot)
        return first

    def _prerequisites(self, plan: PlanCandidate) -> list[Violation]:
        first = self._first_slot(plan)
        violations = []
        for objective in self.syllabus.objectives:
            if objective.id not in first:
                continue
            for pre in objective.prerequisites:
                # Absent du plan : deja signale par _coverage, inutile de le repeter.
                if pre not in first:
                    continue
                if first[pre] >= first[objective.id]:
                    violations.append(
                        Violation(
                            kind=ViolationKind.PREREQUISITE,
                            explanation=(
                                f"'{objective.id}' est enseigne au creneau {first[objective.id]}, "
                                f"mais son prerequis '{pre}' l'est au creneau {first[pre]}. "
                                f"Le prerequis doit venir avant."
                            ),
                            involved=(pre, objective.id),
                        )
                    )
        return violations

    def _overlap(self, plan: PlanCandidate) -> list[Violation]:
        ordered = sorted(plan.sessions, key=lambda s: s.start_slot)
        return [
            Violation(
                kind=ViolationKind.OVERLAP,
                explanation=(
                    f"'{left.title}' occupe [{left.start_slot}, {left.end_slot}) et chevauche "
                    f"'{right.title}' qui demarre au creneau {right.start_slot}."
                ),
                involved=(left.title, right.title),
            )
            for left, right in zip(ordered, ordered[1:])
            if left.end_slot > right.start_slot
        ]

    def _duration(self, plan: PlanCandidate) -> list[Violation]:
        lo, hi = self.syllabus.min_duration, self.syllabus.max_duration
        return [
            Violation(
                kind=ViolationKind.DURATION,
                explanation=(
                    f"'{s.title}' dure {s.duration} creneaux, hors des bornes [{lo}, {hi}]."
                ),
                involved=(s.title,),
            )
            for s in plan.sessions
            if not lo <= s.duration <= hi
        ]

    def is_instance_feasible(self) -> tuple[bool, list[str]]:
        """Existe-t-il au moins un ordre de creneaux respectant les prerequis ?

        A appeler avant la boucle : si le syllabus contient un cycle, aucun plan n'existe et
        le LLM echouerait jusqu'a epuisement du budget sans qu'on sache pourquoi.

        Chaque arc de prerequis est pose sous un literal d'hypothese. Si le modele est
        infaisable, CP-SAT rend le sous-ensemble suffisant d'hypotheses en cause, ce qui
        identifie exactement les arcs du cycle.
        """
        model = cp_model.CpModel()
        slot = {
            o.id: model.NewIntVar(0, self.syllabus.n_sessions - 1, f"slot_{o.id}")
            for o in self.syllabus.objectives
        }

        assumptions: dict[tuple[str, str], cp_model.IntVar] = {}
        for objective in self.syllabus.objectives:
            for pre in objective.prerequisites:
                if pre not in slot:
                    continue
                literal = model.NewBoolVar(f"pre_{pre}_{objective.id}")
                model.Add(slot[pre] < slot[objective.id]).OnlyEnforceIf(literal)
                assumptions[(pre, objective.id)] = literal

        model.AddAssumptions(list(assumptions.values()))
        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return True, []

        core = set(solver.SufficientAssumptionsForInfeasibility())
        reasons = [
            f"Prerequis insatisfiable : '{pre}' doit preceder '{obj}'."
            for (pre, obj), literal in assumptions.items()
            if literal.Index() in core
        ]
        return False, reasons or ["Instance infaisable (verifier les bornes du syllabus)."]

    def solve(self) -> PlanCandidate | None:
        """Baseline CSP pur : un plan valide par construction, sans LLM.

        Une session par creneau, un objectif par session, ordonnes par niveau de prerequis.
        Les titres sont generiques : c'est le point de comparaison avec le LLM.
        """
        model = cp_model.CpModel()
        n = self.syllabus.n_sessions
        slot = {
            o.id: model.NewIntVar(0, n - 1, f"slot_{o.id}") for o in self.syllabus.objectives
        }

        for objective in self.syllabus.objectives:
            for pre in objective.prerequisites:
                if pre in slot:
                    model.Add(slot[pre] < slot[objective.id])

        solver = cp_model.CpSolver()
        if solver.Solve(model) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None

        by_slot: dict[int, list[str]] = {}
        for oid, var in slot.items():
            by_slot.setdefault(solver.Value(var), []).append(oid)

        sessions = tuple(
            Session(
                index=i,
                title=f"Session {i + 1}",
                objectives=tuple(sorted(by_slot[s])),
                start_slot=i * self.syllabus.min_duration,
                duration=self.syllabus.min_duration,
            )
            for i, s in enumerate(sorted(by_slot))
        )
        return PlanCandidate(sessions=sessions)
