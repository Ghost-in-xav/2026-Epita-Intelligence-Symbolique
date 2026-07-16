"""Agent de validation SHACL.

Valide le graphe d'un document (asserté + éventuellement inféré) contre les
shapes SHACL du projet via *pySHACL*. Le rapport de validation, lui-même un
graphe RDF conforme au vocabulaire ``sh:``, est persisté dans le graphe
``urn:graph:reports`` du blackboard — la provenance des violations reste donc
interrogeable en SPARQL. Émet ``ValidationSucceeded`` ou ``ViolationDetected``.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from pyshacl import validate
from rdflib import Graph, Namespace

from ..events import VALIDATION_SUCCEEDED, VIOLATION_DETECTED, SemanticEvent
from .base import Agent

SH = Namespace("http://www.w3.org/ns/shacl#")


class ValidationAgent(Agent):
    name = "ValidationAgent"
    handles = ("validate", "revalidate")

    def __init__(self, blackboard, shapes_path: Path) -> None:
        super().__init__(blackboard)
        self.shapes = Graph().parse(shapes_path)
        # Nombre de contraintes réellement évaluées : les property shapes (le
        # plus souvent des nœuds anonymes non typés ``sh:PropertyShape``) et les
        # contraintes SPARQL — et non le seul décompte des NodeShapes.
        self.constraint_count = (len(list(self.shapes.objects(None, SH.property))) +
                                 len(list(self.shapes.objects(None, SH["sparql"]))))

    def _execute(self, action: str, doc_uri: str) -> SemanticEvent:
        include_inferred = action == "revalidate"
        data = (self.blackboard.combined_doc_graph(doc_uri)
                if include_inferred else self.blackboard.doc_graph(doc_uri))

        conforms, report_graph, _ = validate(
            data_graph=data,
            shacl_graph=self.shapes,
            ont_graph=self.blackboard.ontology,
            inference="none",          # l'inférence est le rôle du ReasoningAgent
            advanced=True,             # active les contraintes SPARQL
            abort_on_first=False,
        )

        # Persistance du rapport dans le graphe de connaissances partagé
        reports = self.blackboard.reports_graph
        for triple in report_graph:
            reports.add(triple)

        violations = self._summarize(report_graph)
        meta = self.blackboard.documents[doc_uri]

        if conforms:
            meta["status"] = "revalidated" if include_inferred else "validated"
            return self.emit(VALIDATION_SUCCEEDED, doc_uri,
                             stage=action, constraintsEvaluated=self.constraint_count)

        meta["status"] = "failed"
        meta["violations"] = violations
        return self.emit(VIOLATION_DETECTED, doc_uri,
                         stage=action,
                         violationCount=len(violations),
                         constraintsEvaluated=self.constraint_count,
                         details="; ".join(v["message"] for v in violations[:5]))

    @staticmethod
    def _summarize(report: Graph) -> List[dict]:
        violations = []
        for result in report.subjects(None, SH.ValidationResult):
            violations.append({
                "focus": str(report.value(result, SH.focusNode) or ""),
                "path": str(report.value(result, SH.resultPath) or ""),
                "severity": str(report.value(result, SH.resultSeverity) or "").split("#")[-1],
                "message": str(report.value(result, SH.resultMessage) or ""),
            })
        return violations
