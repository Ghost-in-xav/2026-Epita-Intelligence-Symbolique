"""Agent d'extraction et de transformation (ETL) de documents RDF.

Détecte le format de sérialisation (Turtle, RDF/XML, JSON-LD, N-Triples,
TriG, N3), parse le document et charge les triplets dans le graphe nommé du
document au sein du blackboard. En cas d'échec de parsing, l'évènement
``ExtractionFailed`` déclenche la replanification de l'orchestrateur (route de
quarantaine).
"""

from __future__ import annotations

import logging
from pathlib import Path

logging.getLogger("rdflib").setLevel(logging.ERROR)

from rdflib import Graph
from rdflib.util import guess_format

from ..events import EXTRACTION_COMPLETED, EXTRACTION_FAILED, SemanticEvent
from .base import Agent

_FALLBACK_FORMATS = ("turtle", "xml", "json-ld", "nt", "trig", "n3")


class ExtractionAgent(Agent):
    name = "ExtractionAgent"
    handles = ("extract",)

    def _execute(self, action: str, doc_uri: str) -> SemanticEvent:
        meta = self.blackboard.documents[doc_uri]
        path: Path = meta["path"]
        fmt = guess_format(str(path))

        parsed, used_format, error = None, None, None
        candidates = [fmt] + [f for f in _FALLBACK_FORMATS if f != fmt] if fmt else list(_FALLBACK_FORMATS)
        for candidate in candidates:
            try:
                g = Graph()
                g.parse(path, format=candidate)
                if len(g) == 0 and candidate != candidates[-1]:
                    continue
                parsed, used_format = g, candidate
                break
            except Exception as exc:  # noqa: BLE001 - on tente le format suivant
                error = str(exc)

        if parsed is None or len(parsed) == 0:
            meta["status"] = "failed"
            return self.emit(EXTRACTION_FAILED, doc_uri,
                             reason=error or "document vide",
                             file=str(path.name))

        target = self.blackboard.doc_graph(doc_uri)
        for triple in parsed:
            target.add(triple)

        meta.update(status="extracted", format=used_format, triples=len(target))
        return self.emit(EXTRACTION_COMPLETED, doc_uri,
                         format=used_format, triples=len(target),
                         file=str(path.name))
