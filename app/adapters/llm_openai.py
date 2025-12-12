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
        usage = dict(resp.usage) if resp.usage else {}
        return msg, usage

    def chat_stream(self, system: str, user: str, temperature: float, max_tokens: int):
        stream = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[{"role":"system","content":system}, {"role":"user","content":user}],
            stream=True
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
