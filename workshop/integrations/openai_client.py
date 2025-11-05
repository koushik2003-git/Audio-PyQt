
import os
import json
from typing import Optional
from dotenv import load_dotenv
try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # type: ignore
from .utils.logger import get_logger

load_dotenv()

class OpenAIClient:
    """Thin wrapper with offline fallbacks to keep UI functional without API key."""
    def __init__(self, model_gpt: str = "gpt-4o", model_lite: str = "gpt-4o-mini"):
        self.logger = get_logger("workshop.openai")
        self.model_gpt = model_gpt
        self.model_lite = model_lite
        key = os.getenv("OPENAI_API_KEY", "").strip()
        self._enabled = bool(key and OpenAI is not None)
        if self._enabled:
            self.client = OpenAI(api_key=key)
            self.logger.info("OpenAI client initialized.")
        else:
            self.client = None
            self.logger.warning("OPENAI_API_KEY not set. Using offline stub responses.")

    # ---- Offline helpers
    def _offline_questions(self) -> str:
        cats = ["Strategy","Operations","Risk","Finance","People","Technology"]
        out = [{"category": cats[i%6], "role": ("CEO" if i%3==0 else None),
                "text": f"What are the top {i+1} priorities for the next 12 months?"}
               for i in range(12)]
        return json.dumps(out, ensure_ascii=False)

    def _offline_sim_results(self, n:int) -> str:
        return json.dumps([{"response":"(offline) A reasonable, concise answer reflecting alignment.",
                            "score":0.6} for _ in range(max(1,n))])

    def _offline(self, prompt: str) -> str:
        if "Generate 10–14 questions" in prompt or "Generate 10-14 questions" in prompt:
            return self._offline_questions()
        if '"response"' in prompt and '"score"' in prompt and "Questions:" in prompt:
            # try to count questions
            try:
                part = prompt.split("Questions:",1)[1]
                start = part.index("["); end = part.rindex("]")+1
                n = len(json.loads(part[start:end]))
            except Exception:
                n = 10
            return self._offline_sim_results(n)
        return "This is an offline placeholder response generated without calling the OpenAI API."

    # ---- Public calls
    def complete_text(self, prompt: str, model: Optional[str]=None, temperature: float=0.5) -> str:
        if not self._enabled:
            return self._offline(prompt)
        used = model or self.model_lite
        resp = self.client.chat.completions.create(
            model=used,
            messages=[
                {"role":"system","content":"You are a concise business analyst."},
                {"role":"user","content":prompt},
            ],
            temperature=temperature,
        )
        return resp.choices[0].message.content

    def complete_json(self, prompt: str, model: Optional[str]=None, temperature: float=0.2) -> str:
        txt = self.complete_text(prompt, model=model, temperature=temperature)
        a = txt.find("["); b = txt.rfind("]")+1
        if a!=-1 and b!=-1: return txt[a:b]
        a = txt.find("{"); b = txt.rfind("}")+1
        if a!=-1 and b!=-1: return txt[a:b]
        return txt
