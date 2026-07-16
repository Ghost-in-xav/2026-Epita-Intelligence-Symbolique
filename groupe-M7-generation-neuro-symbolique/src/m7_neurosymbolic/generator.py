"""Generateurs de plans : Semantic Kernel, et une version scriptee pour les tests."""

from __future__ import annotations

import json
import os
from typing import Protocol

from .schema import PlanCandidate

SYSTEM_PROMPT = """Tu es un concepteur pedagogique. Tu produis des plans de cours structures.

Tu reponds uniquement par un objet JSON valide, sans texte autour :

{"sessions": [{"title": "...", "objectives": ["OBJ1"], "start_slot": 0, "duration": 2}]}

Regles :
- "objectives" ne contient que des identifiants presents dans le syllabus.
- Les sessions ne se chevauchent pas.
- "duration" respecte les bornes du syllabus.
- Un objectif vient apres tous ses prerequis.
- Les titres sont specifiques, pas generiques.
"""


class Generator(Protocol):
    """Interface commune. La boucle ne sait pas si elle parle a un LLM ou a un script."""

    async def generate(self, syllabus_json: str, feedback: str = "") -> str: ...


def parse_plan(raw: str) -> PlanCandidate:
    """Parse la reponse. Tolere les cloture markdown que les modeles ajoutent malgre tout."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = "\n".join(
            line for line in cleaned.splitlines() if not line.strip().startswith("```")
        )
    return PlanCandidate.from_json(cleaned)


class ScriptedGenerator:
    """Rejoue une liste de reponses fixees.

    Sert a tester la boucle sans reseau ni cle API : le comportement est deterministe, donc
    les tests sont reproductibles et gratuits.
    """

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[str] = []

    async def generate(self, syllabus_json: str, feedback: str = "") -> str:
        self.calls.append(feedback)
        if not self.responses:
            raise RuntimeError("ScriptedGenerator : plus de reponse disponible.")
        return self.responses.pop(0)


class SemanticKernelGenerator:
    """Generateur reel, via Semantic Kernel.

    Le plan precedent est reinjecte avec le feedback : sans lui, le modele repart de zero et
    casse ce qui etait deja correct.
    """

    def __init__(self, model_id: str | None = None) -> None:
        from semantic_kernel import Kernel
        from semantic_kernel.connectors.ai.open_ai import (
            OpenAIChatCompletion,
            OpenAIChatPromptExecutionSettings,
        )

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY absent. Renseigne le fichier .env.")

        self.kernel = Kernel()
        self.service = OpenAIChatCompletion(
            service_id="generator",
            ai_model_id=model_id or os.getenv("M7_MODEL", "gpt-4o-mini"),
            api_key=api_key,
        )
        self.kernel.add_service(self.service)
        self.settings = OpenAIChatPromptExecutionSettings(
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        self.last_plan: str | None = None

    async def generate(self, syllabus_json: str, feedback: str = "") -> str:
        from semantic_kernel.contents import ChatHistory

        history = ChatHistory()
        history.add_system_message(SYSTEM_PROMPT)
        history.add_user_message(f"Syllabus :\n{syllabus_json}")

        if feedback and self.last_plan:
            history.add_assistant_message(self.last_plan)
            history.add_user_message(feedback)

        response = await self.service.get_chat_message_content(
            chat_history=history, settings=self.settings
        )
        raw = str(response)
        self.last_plan = raw
        return raw


def load_scripted_from_file(path: str) -> ScriptedGenerator:
    """Charge des reponses enregistrees (utile pour rejouer un run en demo hors-ligne)."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return ScriptedGenerator([json.dumps(item, ensure_ascii=False) for item in data["responses"]])
