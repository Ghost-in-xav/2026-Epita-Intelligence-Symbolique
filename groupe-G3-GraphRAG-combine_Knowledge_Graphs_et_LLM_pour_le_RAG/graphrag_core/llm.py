import os
from abc import ABC, abstractmethod
from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI

class LLMClient(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str:
        pass

class OpenAIClient(LLMClient):
    def __init__(self, model: str, api_key: str):
        self._client = OpenAI(api_key=api_key)
        self.model = model

    def complete(self, prompt: str) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.choices[0].message.content

class AnthropicClient(LLMClient):
    def __init__(self, model: str, api_key: str):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def complete(self, prompt: str) -> str:
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return msg.content[0].text

class OllamaClient(LLMClient):
    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url

    def complete(self, prompt: str) -> str:
        import requests
        resp = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=120
        )
        return resp.json()["response"]

def get_llm_client() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "openai")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    if provider == "openai":
        return OpenAIClient(model=model, api_key=os.environ["OPENAI_API_KEY"])
    elif provider == "anthropic":
        return AnthropicClient(model=model, api_key=os.environ["ANTHROPIC_API_KEY"])
    elif provider == "ollama":
        return OllamaClient(model=model, base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
