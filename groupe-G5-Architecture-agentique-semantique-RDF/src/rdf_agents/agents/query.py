"""Agent de requêtage et de partitionnement SPARQL.

Rôles :
1. **Partitionnement** : segmente le graphe (asserté + inféré) d'un document
   en partitions thématiques par classe (une requête CONSTRUCT par classe
   cible), stockées comme graphes nommés ``urn:graph:partition:<id>:<classe>``.
2. **Indexation** : exécute une requête d'agrégation SPARQL et mémorise les
   statistiques d'entités par type, exploitées par la couche d'évaluation.
3. **Requêtage inter-graphes** : expose ``federated_query`` pour interroger
   l'union des graphes du blackboard (hors journal d'évènements).
"""

from __future__ import annotations

from typing import Dict

from rdflib import URIRef

from ..events import INDEXING_COMPLETED, SemanticEvent
from .base import Agent

PARTITION_CLASSES = {
    "datasets": "http://www.w3.org/ns/dcat#Dataset",
    "distributions": "http://www.w3.org/ns/dcat#Distribution",
    "organizations": "http://xmlns.com/foaf/0.1/Organization",
    "persons": "http://xmlns.com/foaf/0.1/Person",
}

_PARTITION_QUERY = """
CONSTRUCT {{ ?s ?p ?o }}
WHERE {{
  ?s a <{cls}> ; ?p ?o .
}}
"""

_STATS_QUERY = """
SELECT ?type (COUNT(DISTINCT ?s) AS ?n)
WHERE { ?s a ?type }
GROUP BY ?type ORDER BY DESC(?n)
"""


class QueryAgent(Agent):
    name = "QueryAgent"
    handles = ("index",)

    def _execute(self, action: str, doc_uri: str) -> SemanticEvent:
        combined = self.blackboard.combined_doc_graph(doc_uri)
        doc_id = doc_uri.rsplit(":", 1)[-1]

        partition_sizes: Dict[str, int] = {}
        for label, cls in PARTITION_CLASSES.items():
            constructed = combined.query(_PARTITION_QUERY.format(cls=cls)).graph
            if constructed is None or len(constructed) == 0:
                continue
            target = self.blackboard.dataset.graph(
                URIRef(f"urn:graph:partition:{doc_id}:{label}"))
            for triple in constructed:
                target.add(triple)
            partition_sizes[label] = len(constructed)

        type_stats = {str(row.type): int(row.n)
                      for row in combined.query(_STATS_QUERY)}

        meta = self.blackboard.documents[doc_uri]
        meta.update(status="indexed", partitions=partition_sizes,
                    entity_types=type_stats)

        return self.emit(INDEXING_COMPLETED, doc_uri,
                         partitions=len(partition_sizes),
                         partitionedTriples=sum(partition_sizes.values()),
                         distinctTypes=len(type_stats))

    # -------------------------------------------------------- requêtage global
    def federated_query(self, sparql: str):
        """Requête SPARQL sur l'union des graphes du blackboard (hors journal
        d'évènements). Attention : inclut aussi les documents en quarantaine."""
        return self.blackboard.query(sparql)
