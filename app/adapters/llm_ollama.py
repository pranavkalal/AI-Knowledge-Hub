"""
LLM adapter for local inference via Ollama (http://localhost:11434).
No tokens, no bills. Good for dev and demos.
"""

from typing import Tuple, Dict
import requests
from app.ports import LLMPort

class OllamaAdapter(LLMPort):
    def __init__(self, model: str = "llama3.1", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host.rstrip("/")

    def chat(self, system: str, user: str, temperature: float, max_tokens: int) -> Tuple[str, Dict]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {
                "temperature": float(temperature),
                "num_predict": int(max_tokens),
            },
            "stream": False,
        }
        r = requests.post(f"{self.host}/api/chat", json=payload, timeout=120)
        r.raise_for_status()
        data = r.json()
        msg = data.get("message", {}).get("content", "")
        return msg, {"provider": "ollama", "model": self.model}
