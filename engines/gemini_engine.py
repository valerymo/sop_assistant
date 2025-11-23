import requests
from .base import BaseEngine

class GeminiEngine(BaseEngine):
    def generate(self, prompt: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"prompt": prompt}
        response = requests.post("https://api.gemini.com/v1/query", json=payload, headers=headers)
        data = response.json()
        return data.get("result", "[No response from Gemini]")
