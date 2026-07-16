"""Hotes LLM pour le serveur MCP d'analyse symbolique.

Le serveur MCP est agnostique du LLM. Ce sous-paquet fournit un *hote* de
reference base sur Gemini (`gemini_host`) qui : se connecte au serveur MCP,
expose ses outils a Gemini, laisse le LLM orchestrer les appels, et trace la
chaine LLM -> outil symbolique (support de l'evaluation).
"""

__all__ = ["GeminiMCPHost"]


def __getattr__(name: str):
    if name == "GeminiMCPHost":
        from .gemini_host import GeminiMCPHost

        return GeminiMCPHost
    raise AttributeError(name)
