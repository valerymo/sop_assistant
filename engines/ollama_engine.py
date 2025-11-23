# engines/ollama_engine.py
from .base import BaseEngine
from langchain_ollama import OllamaLLM

class OllamaEngine(BaseEngine):
    """Wrapper for Ollama LLM."""

    def __init__(self, name: str, model_name: str = "mistral"):
        super().__init__(name)
        self.llm = OllamaLLM(model=model_name)

    def generate(self, prompt: str) -> str:
        return self.llm.invoke(prompt)
