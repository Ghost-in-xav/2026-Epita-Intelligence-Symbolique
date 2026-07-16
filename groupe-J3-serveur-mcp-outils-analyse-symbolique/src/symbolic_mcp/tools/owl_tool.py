"""Outil OWL — raisonnement sur ontologies via owlready2 + reasoner HermiT.

Prend une ontologie (RDF/XML ou Turtle), lance un reasoner OWL (HermiT, en
Java) et renvoie : la coherence de l'ontologie, les classes insatisfiables, la
hierarchie de classes *inferee* et les types *inferes* des individus.

Necessite un JRE (Java) sur la machine — HermiT est un reasoner Java embarque
par owlready2.
"""

from __future__ import annotations

import contextlib
import os
import sys
import tempfile
from typing import Any

import owlready2


def _to_rdfxml_bytes(ontology: str, fmt: str) -> bytes:
    """Normalise l'ontologie en RDF/XML (owlready2 ne lit pas le Turtle nativement)."""
    fmt = (fmt or "rdfxml").lower()
    if fmt in ("rdfxml", "owl", "xml", "rdf/xml", "rdf"):
        return ontology.encode("utf-8")
    if fmt in ("turtle", "ttl", "n3", "nt", "ntriples"):
        import rdflib

        rdflib_fmt = {"ttl": "turtle", "nt": "nt", "ntriples": "nt"}.get(fmt, fmt)
        graph = rdflib.Graph()
        graph.parse(data=ontology, format=rdflib_fmt)
        return graph.serialize(format="xml").encode("utf-8")
    raise ValueError(f"Format d'ontologie non supporte : {fmt!r}")


_BUILTIN = {"Thing", "Nothing"}


def _remove_temp_file(path: str | None) -> None:
    if not path:
        return
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def _named_parents(cls) -> list[str]:
    return sorted(
        {
            p.name
            for p in cls.is_a
            if isinstance(p, owlready2.ThingClass) and p.name and p.name not in _BUILTIN
        }
    )


def owl_reason(
    ontology: str,
    fmt: str = "rdfxml",
    operation: str = "consistency",
    target: str | None = None,
) -> dict[str, Any]:
    """Raisonne sur une ontologie OWL et renvoie coherence + inferences.

    Args:
        ontology: le contenu de l'ontologie (texte).
        fmt: "rdfxml" (defaut) ou "turtle".
        operation: "consistency" (coherence + classes insatisfiables),
            "classify" (hierarchie de classes inferee + types des individus),
            ou "query" (focalise sur l'entite `target`).
        target: nom de la classe ou de l'individu a inspecter (operation "query").

    Returns:
        dict avec `consistent` (bool), `unsatisfiable_classes`, et selon
        l'operation la hierarchie inferee / les types d'individus / le focus,
        plus un `summary` en langage naturel.
    """
    if not isinstance(ontology, str) or not ontology.strip():
        return {"ok": False, "tool": "owl_reason", "error": "Ontologie vide."}
    if not isinstance(operation, str) or operation.lower() not in {
        "consistency",
        "classify",
        "query",
    }:
        return {
            "ok": False,
            "tool": "owl_reason",
            "error": f"Operation OWL non supportee : {operation!r}.",
        }
    operation = operation.lower()
    if operation == "query" and (not isinstance(target, str) or not target.strip()):
        return {
            "ok": False,
            "tool": "owl_reason",
            "error": "Le champ 'target' est requis pour l'operation 'query'.",
        }

    try:
        data = _to_rdfxml_bytes(ontology, fmt)
    except Exception as exc:  # conversion / parsing Turtle
        return {"ok": False, "tool": "owl_reason", "error": f"Lecture de l'ontologie : {exc}"}

    world = owlready2.World()
    tmp_path: str | None = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".owl")
        os.write(fd, data)
        os.close(fd)
        onto = world.get_ontology("file://" + tmp_path).load()
    except Exception as exc:
        _remove_temp_file(tmp_path)
        return {"ok": False, "tool": "owl_reason", "error": f"Chargement de l'ontologie : {exc}"}
    _remove_temp_file(tmp_path)
    tmp_path = None

    consistent = True
    try:
        # HermiT ecrit parfois sur stdout : on redirige vers stderr pour ne pas
        # corrompre le transport MCP (qui utilise stdout pour le protocole).
        with contextlib.redirect_stdout(sys.stderr):
            owlready2.sync_reasoner(world, debug=0)
    except owlready2.OwlReadyInconsistentOntologyError:
        consistent = False
    except FileNotFoundError:
        return {
            "ok": False,
            "tool": "owl_reason",
            "error": "Reasoner HermiT introuvable : un JRE (Java) doit etre installe et dans le PATH.",
        }
    except Exception as exc:  # pragma: no cover - erreurs Java diverses
        return {"ok": False, "tool": "owl_reason", "error": f"Echec du raisonnement : {exc}"}

    unsat = sorted({c.name for c in world.inconsistent_classes() if getattr(c, "name", None)})

    result: dict[str, Any] = {
        "ok": True,
        "tool": "owl_reason",
        "operation": operation,
        "consistent": consistent,
        "unsatisfiable_classes": unsat,
    }

    if not consistent:
        result["summary"] = (
            "INCOHERENTE — l'ontologie contient une contradiction logique : "
            "le reasoner a derive owl:Nothing (aucun modele possible)."
        )
        return result

    # On itere au niveau du World (et pas de `onto`) car les entites peuvent
    # appartenir a un namespace different de l'IRI de l'ontologie chargee.
    classes = [
        c for c in world.classes() if getattr(c, "name", None) and c.name not in _BUILTIN
    ]
    # world.individuals() n'indexe que les owl:NamedIndividual explicites : on
    # enumere plutot les instances de chaque classe (couvre les individus types
    # implicitement, comme `:rex a :Dog`).
    individuals = sorted(
        {ind for c in classes for ind in c.instances() if getattr(ind, "name", None)},
        key=lambda e: e.name,
    )

    if operation == "query" and target:
        entity = next(
            (e for e in (*classes, *individuals) if e.name == target), None
        )
        if entity is None:
            result["error"] = f"Entite '{target}' introuvable dans l'ontologie."
            result["ok"] = False
            return result
        if isinstance(entity, owlready2.ThingClass):
            result["focus"] = {
                "class": target,
                "inferred_superclasses": sorted(
                    {
                        a.name
                        for a in entity.ancestors()
                        if a is not entity and getattr(a, "name", None) and a.name not in _BUILTIN
                    }
                ),
                "inferred_subclasses": sorted(
                    {
                        d.name
                        for d in entity.descendants()
                        if d is not entity and getattr(d, "name", None) and d.name not in _BUILTIN
                    }
                ),
            }
            result["summary"] = f"Classe '{target}' : hierarchie inferee calculee."
        else:
            types = sorted(
                {
                    t.name
                    for t in entity.INDIRECT_is_a
                    if getattr(t, "name", None) and t.name not in _BUILTIN
                }
            )
            result["focus"] = {"individual": target, "inferred_types": types}
            result["summary"] = f"Individu '{target}' : types inferes = {', '.join(types) or '(aucun)'}."
        return result

    # operation "classify" ou "consistency" : rapport complet des inferences
    hierarchy = {c.name: _named_parents(c) for c in classes}
    individual_types = {
        ind.name: sorted(
            {
                t.name
                for t in ind.INDIRECT_is_a
                if getattr(t, "name", None) and t.name not in _BUILTIN
            }
        )
        for ind in individuals
    }
    result["class_hierarchy"] = hierarchy
    result["individual_types"] = individual_types
    result["summary"] = (
        f"COHERENTE — {len(classes)} classes, {len(individuals)} individus. "
        + (
            f"Classes insatisfiables : {', '.join(unsat)}. "
            if unsat
            else "Aucune classe insatisfiable. "
        )
        + "Hierarchie et types inferes disponibles dans le resultat."
    )
    return result
