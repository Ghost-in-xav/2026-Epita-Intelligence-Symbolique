"""Modele de domaine : syllabus en entree, plan de cours en sortie."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


@dataclass(frozen=True)
class LearningObjective:
    id: str
    label: str
    prerequisites: tuple[str, ...] = ()


@dataclass(frozen=True)
class Syllabus:
    objectives: tuple[LearningObjective, ...]
    n_sessions: int
    min_duration: int
    max_duration: int

    @property
    def objective_ids(self) -> set[str]:
        return {o.id for o in self.objectives}

    @staticmethod
    def from_json(path: str | Path) -> "Syllabus":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        objectives = tuple(
            LearningObjective(
                id=item["id"],
                label=item["label"],
                prerequisites=tuple(item.get("prerequisites", [])),
            )
            for item in data["objectives"]
        )
        return Syllabus(
            objectives=objectives,
            n_sessions=data["n_sessions"],
            min_duration=data["min_duration"],
            max_duration=data["max_duration"],
        )

    def to_prompt_json(self) -> str:
        return json.dumps(
            {
                "objectives": [
                    {"id": o.id, "label": o.label, "prerequisites": list(o.prerequisites)}
                    for o in self.objectives
                ],
                "n_sessions": self.n_sessions,
                "min_duration": self.min_duration,
                "max_duration": self.max_duration,
            },
            indent=2,
            ensure_ascii=False,
        )


@dataclass(frozen=True)
class Session:
    index: int
    title: str
    objectives: tuple[str, ...]
    start_slot: int
    duration: int

    @property
    def end_slot(self) -> int:
        return self.start_slot + self.duration


@dataclass(frozen=True)
class PlanCandidate:
    sessions: tuple[Session, ...]

    @staticmethod
    def from_json(raw: str | dict) -> "PlanCandidate":
        data = json.loads(raw) if isinstance(raw, str) else raw
        return PlanCandidate(
            sessions=tuple(
                Session(
                    index=i,
                    title=item["title"],
                    objectives=tuple(item["objectives"]),
                    start_slot=item["start_slot"],
                    duration=item["duration"],
                )
                for i, item in enumerate(data["sessions"])
            )
        )

    def to_json(self) -> str:
        return json.dumps(
            {
                "sessions": [
                    {
                        "title": s.title,
                        "objectives": list(s.objectives),
                        "start_slot": s.start_slot,
                        "duration": s.duration,
                    }
                    for s in self.sessions
                ]
            },
            indent=2,
            ensure_ascii=False,
        )


class ViolationKind(str, Enum):
    COVERAGE = "coverage"
    PREREQUISITE = "prerequisite"
    OVERLAP = "overlap"
    DURATION = "duration"
    UNKNOWN_OBJECTIVE = "unknown_objective"


@dataclass(frozen=True)
class Violation:
    kind: ViolationKind
    explanation: str
    involved: tuple[str, ...] = ()


@dataclass
class ValidationResult:
    is_valid: bool
    violations: list[Violation] = field(default_factory=list)

    def summary(self) -> str:
        if self.is_valid:
            return "Plan valide."
        return f"{len(self.violations)} violation(s): " + ", ".join(
            v.kind.value for v in self.violations
        )
