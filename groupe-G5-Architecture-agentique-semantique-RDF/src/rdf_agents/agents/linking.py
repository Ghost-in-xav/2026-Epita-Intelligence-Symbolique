"""Agent de synchronisation avec les sources Linked Data externes.

Aligne les entités locales (organisations, lieux, concepts) sur DBpedia et
Wikidata via une résolution par label (``rdfs:label`` / ``foaf:name`` /
``dct:title`` / ``skos:prefLabel``, insensible à la casse et aux accents). Les
correspondances produisent des liens ``owl:sameAs`` matérialisés dans
``urn:graph:links``.

Le liage s'appuie sur un **cache local** (``data/linked_data_cache/``) pour
rester reproductible hors-ligne. L'interrogation directe des endpoints SPARQL
publics de DBpedia/Wikidata (avec repli sur le cache) est une extension prévue
mais **non implémentée** à ce stade.
"""

from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Dict, List

from rdflib import Graph, Namespace, OWL, RDF, RDFS, URIRef

from ..events import LINKING_COMPLETED, SemanticEvent
from .base import Agent

FOAF = Namespace("http://xmlns.com/foaf/0.1/")
DCT = Namespace("http://purl.org/dc/terms/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")

#: types dont les instances ne sont pas des entités à aligner (un jeu de
#: données ou une distribution n'a pas d'équivalent owl:sameAs sur DBpedia)
_NON_ENTITY_TYPES = (DCAT.Dataset, DCAT.Distribution)

_LABEL_PROPS = (RDFS.label, FOAF.name, DCT.title, SKOS.prefLabel)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).casefold().strip()


class LinkingAgent(Agent):
    name = "LinkingAgent"
    handles = ("link",)

    def __init__(self, blackboard, cache_dir: Path) -> None:
        super().__init__(blackboard)
        self.remote_index: Dict[str, List[URIRef]] = {}
        for file in sorted(Path(cache_dir).glob("*.ttl")):
            g = Graph().parse(file)
            for prop in _LABEL_PROPS:
                for subject, label in g.subject_objects(prop):
                    self.remote_index.setdefault(_norm(str(label)), []).append(subject)

    def _execute(self, action: str, doc_uri: str) -> SemanticEvent:
        combined = self.blackboard.combined_doc_graph(doc_uri)
        links_graph = self.blackboard.links_graph

        # Garde de type : l'égalité de label ne suffit pas à établir owl:sameAs
        # (identité forte). On exclut les sujets typés comme jeu de données /
        # distribution, dont un titre homonyme d'une entité DBpedia (p.ex. une
        # ville) provoquerait une fusion d'identités erronée.
        non_entity = {s for t in _NON_ENTITY_TYPES
                      for s in combined.subjects(RDF.type, t)}

        candidates = 0
        links = 0
        seen_pairs = set()
        for prop in _LABEL_PROPS:
            for subject, label in combined.subject_objects(prop):
                if not isinstance(subject, URIRef) or subject in non_entity:
                    continue
                candidates += 1
                for remote in self.remote_index.get(_norm(str(label)), []):
                    if remote == subject or (subject, remote) in seen_pairs:
                        continue
                    # owl:sameAs est symétrique : un seul triplet par lien, pour
                    # que le compteur sameAsLinks corresponde au graphe produit.
                    links_graph.add((subject, OWL.sameAs, remote))
                    seen_pairs.add((subject, remote))
                    links += 1

        meta = self.blackboard.documents[doc_uri]
        meta.update(status="linked", sameas_links=links)
        return self.emit(LINKING_COMPLETED, doc_uri,
                         candidates=candidates, sameAsLinks=links)
