# app/adapters/llm_ollama.py
import os, requests

class OllamaAdapter:
    def __init__(self, model: str, host: str | None = None, timeout: int = 120):
        self.model = model
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.timeout = timeout

    def _raise(self, r):
        # Try to extract Ollama's JSON error; otherwise show plain text
        try:
            msg = r.json().get("error")
        except Exception:
            msg = r.text
        raise RuntimeError(f"Ollama {r.status_code}: {msg}")

    def chat(self, system: str, user: str, temperature: float, max_tokens: int):
        # Prefer chat; older daemons lack it.
        chat_url = f"{self.host}/api/chat"
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"temperature": temperature, "num_predict": max_tokens},
            "stream": False,
        }
        r = requests.post(chat_url, json=body, timeout=self.timeout)
        if r.status_code == 404:
            # Fall back to /api/generate
            gen_url = f"{self.host}/api/generate"
            prompt = f"{system}\n\n{user}"
            gbody = {
                "model": self.model,
                "prompt": prompt,
                "options": {"temperature": temperature, "num_predict": max_tokens},
                "stream": False,
            }
            rg = requests.post(gen_url, json=gbody, timeout=self.timeout)
            if rg.status_code >= 400:
                self._raise(rg)
            data = rg.json()
            return data.get("response", ""), {"endpoint": "generate"}
        if r.status_code >= 400:
            self._raise(r)
        data = r.json()
        msg = data.get("message", {}).get("content") or data.get("response", "")
        return msg, {"endpoint": "chat"}
