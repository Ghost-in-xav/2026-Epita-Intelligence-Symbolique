"""Planificateur PDDL (sous-ensemble STRIPS typé) écrit from scratch.

Le sous-ensemble supporté couvre : ``:strips``, ``:typing`` et
``:negative-preconditions`` — suffisant pour le domaine ``rdf-pipeline``.
La recherche est une exploration en largeur (BFS) sur l'espace d'états
(ensembles de faits ground), garantissant des plans optimaux en nombre
d'actions. L'orchestrateur utilise ce planificateur en boucle
*plan → exécution → supervision → replanification* : quand l'issue réelle
d'une action (p.ex. une violation SHACL) contredit l'effet attendu,
l'état du monde est corrigé et un nouveau plan est calculé.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

Fact = Tuple[str, ...]  # ("extracted", "doc1")


# --------------------------------------------------------------------- parsing
def _tokenize(text: str) -> List[str]:
    text = re.sub(r";[^\n]*", " ", text)  # commentaires
    return text.replace("(", " ( ").replace(")", " ) ").split()


def _read_sexpr(tokens: List[str], pos: int = 0):
    if tokens[pos] != "(":
        return tokens[pos], pos + 1
    expr, pos = [], pos + 1
    while tokens[pos] != ")":
        node, pos = _read_sexpr(tokens, pos)
        expr.append(node)
    return expr, pos + 1


def _parse_typed_list(items: Sequence[str]) -> List[Tuple[str, str]]:
    """``(?d - document ?x ?y - t)`` -> [(?d, document), (?x, t), (?y, t)]."""
    result, buffer, i = [], [], 0
    while i < len(items):
        if items[i] == "-":
            for name in buffer:
                result.append((name, items[i + 1]))
            buffer, i = [], i + 2
        else:
            buffer.append(items[i])
            i += 1
    for name in buffer:  # non typé
        result.append((name, "object"))
    return result


@dataclass
class Action:
    name: str
    parameters: List[Tuple[str, str]]           # [(?d, document)]
    positive_pre: List[Fact] = field(default_factory=list)
    negative_pre: List[Fact] = field(default_factory=list)
    add_effects: List[Fact] = field(default_factory=list)
    del_effects: List[Fact] = field(default_factory=list)


@dataclass
class GroundAction:
    name: str
    args: Tuple[str, ...]
    positive_pre: FrozenSet[Fact]
    negative_pre: FrozenSet[Fact]
    add_effects: FrozenSet[Fact]
    del_effects: FrozenSet[Fact]

    @property
    def signature(self) -> str:
        return f"({self.name} {' '.join(self.args)})" if self.args else f"({self.name})"

    def applicable(self, state: FrozenSet[Fact]) -> bool:
        return self.positive_pre <= state and not (self.negative_pre & state)

    def apply(self, state: FrozenSet[Fact]) -> FrozenSet[Fact]:
        return (state - self.del_effects) | self.add_effects


class Domain:
    def __init__(self, name: str, actions: List[Action]):
        self.name = name
        self.actions = actions

    @classmethod
    def parse(cls, path: Path) -> "Domain":
        expr, _ = _read_sexpr(_tokenize(Path(path).read_text()))
        assert expr[0] == "define"
        name = expr[1][1]
        actions: List[Action] = []
        for section in expr[2:]:
            if section[0] != ":action":
                continue
            action = Action(name=section[1], parameters=[])
            i = 2
            while i < len(section):
                key, value = section[i], section[i + 1]
                if key == ":parameters":
                    action.parameters = _parse_typed_list(value)
                elif key == ":precondition":
                    _collect(value, action.positive_pre, action.negative_pre)
                elif key == ":effect":
                    _collect(value, action.add_effects, action.del_effects)
                i += 2
            actions.append(action)
        return cls(name, actions)


def _collect(expr, positive: List[Fact], negative: List[Fact]) -> None:
    """Aplati une formule (and ... (not ...) ...) en littéraux."""
    if not expr:
        return
    if expr[0] == "and":
        for sub in expr[1:]:
            _collect(sub, positive, negative)
    elif expr[0] == "not":
        negative.append(tuple(expr[1]))
    else:
        positive.append(tuple(expr))


@dataclass
class Problem:
    objects: Dict[str, str]            # {doc1: document}
    init: FrozenSet[Fact]
    goal_pos: FrozenSet[Fact]
    goal_neg: FrozenSet[Fact]

    @classmethod
    def build(cls, objects: Dict[str, str], init: Sequence[Fact],
              goal: Sequence[Fact], goal_neg: Sequence[Fact] = ()) -> "Problem":
        return cls(dict(objects), frozenset(map(tuple, init)),
                   frozenset(map(tuple, goal)), frozenset(map(tuple, goal_neg)))


# -------------------------------------------------------------------- grounding
def ground_actions(domain: Domain, objects: Dict[str, str]) -> List[GroundAction]:
    by_type: Dict[str, List[str]] = {}
    for obj, typ in objects.items():
        by_type.setdefault(typ, []).append(obj)
        if typ != "object":  # éviter un doublon si l'objet est déjà de type object
            by_type.setdefault("object", []).append(obj)

    grounded: List[GroundAction] = []
    for action in domain.actions:
        domains = [by_type.get(typ, []) for _, typ in action.parameters]
        for combo in product(*domains) if domains else [()]:
            binding = {var: val for (var, _), val in zip(action.parameters, combo)}
            sub = lambda fact: tuple(binding.get(t, t) for t in fact)
            grounded.append(GroundAction(
                name=action.name, args=tuple(combo),
                positive_pre=frozenset(map(sub, action.positive_pre)),
                negative_pre=frozenset(map(sub, action.negative_pre)),
                add_effects=frozenset(map(sub, action.add_effects)),
                del_effects=frozenset(map(sub, action.del_effects)),
            ))
    return grounded


# ---------------------------------------------------------------------- search
def plan(domain: Domain, problem: Problem,
         max_states: int = 100_000) -> Optional[List[GroundAction]]:
    """Recherche en largeur : plan optimal en nombre d'actions, ou None."""
    actions = ground_actions(domain, problem.objects)

    def is_goal(state: FrozenSet[Fact]) -> bool:
        return problem.goal_pos <= state and not (problem.goal_neg & state)

    if is_goal(problem.init):
        return []

    frontier = deque([problem.init])
    parents: Dict[FrozenSet[Fact], Tuple[FrozenSet[Fact], GroundAction]] = {}
    seen = {problem.init}

    while frontier and len(seen) < max_states:
        state = frontier.popleft()
        for action in actions:
            if not action.applicable(state):
                continue
            nxt = action.apply(state)
            if nxt in seen:
                continue
            parents[nxt] = (state, action)
            if is_goal(nxt):
                steps: List[GroundAction] = []
                cur = nxt
                while cur != problem.init:
                    prev, act = parents[cur]
                    steps.append(act)
                    cur = prev
                return list(reversed(steps))
            seen.add(nxt)
            frontier.append(nxt)
    return None
