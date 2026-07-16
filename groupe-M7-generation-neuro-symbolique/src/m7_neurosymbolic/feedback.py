"""Traduction des violations en consignes de correction pour le LLM."""

from __future__ import annotations

from .schema import ValidationResult, ViolationKind

_GUIDANCE: dict[ViolationKind, str] = {
    ViolationKind.COVERAGE: "Ajoute les objectifs manquants a des sessions existantes.",
    ViolationKind.PREREQUISITE: "Reordonne les sessions concernees sans changer leur contenu.",
    ViolationKind.OVERLAP: "Decale les creneaux de depart, garde les durees.",
    ViolationKind.DURATION: "Ajuste la duree ou repartis les objectifs sur plusieurs sessions.",
    ViolationKind.UNKNOWN_OBJECTIVE: "Utilise seulement les identifiants du syllabus.",
}


def build_feedback(result: ValidationResult) -> str:
    """Feedback cible : seulement les contraintes violees, avec quoi faire.

    On ne renvoie pas le syllabus entier a chaque cycle, et on demande une correction plutot
    qu'une regeneration : regenerer de zero casse en general une contrainte deja satisfaite.
    """
    if result.is_valid:
        return ""

    by_kind: dict[ViolationKind, list[str]] = {}
    for violation in result.violations:
        by_kind.setdefault(violation.kind, []).append(violation.explanation)

    lines = ["Le plan precedent viole des contraintes dures. Corrige uniquement ces points :", ""]
    for kind, explanations in by_kind.items():
        lines.append(f"[{kind.value}]")
        lines.extend(f"- {text}" for text in explanations)
        lines.append(f"  Consigne : {_GUIDANCE[kind]}")
        lines.append("")
    lines.append("Garde les titres et la progression deja corrects. Renvoie le plan complet en JSON.")
    return "\n".join(lines)


def build_naive_feedback(result: ValidationResult) -> str:
    """Temoin pour l'ablation : signale l'echec sans dire pourquoi."""
    if result.is_valid:
        return ""
    return "Le plan precedent est invalide. Propose un autre plan au meme format JSON."
