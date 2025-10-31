import requests
from backend.config import settings


class OllamaClient:
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or settings.ollama_host
        self.model = model or settings.ollama_model

    def generate(self, prompt: str) -> str:
        """调用Ollama生成文本"""
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False}
        )
        return response.json()["response"]
