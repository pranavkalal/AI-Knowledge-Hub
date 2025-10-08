from typing import Tuple, Dict
import os
from app.ports import LLMPort
from openai import OpenAI

class OpenAIAdapter(LLMPort):
    def __init__(self, model: str):
        self.model = model
        self.client = OpenAI()

    def chat(self, system: str, user: str, temperature: float, max_tokens: int) -> Tuple[str, Dict]:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[{"role":"system","content":system}, {"role":"user","content":user}]
        )
        msg = resp.choices[0].message.content
        usage = getattr(resp, "usage", None)
        usage = dict(usage) if usage else {}
        return msg, usage
