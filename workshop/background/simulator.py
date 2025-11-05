
import json
from typing import Dict, List
from ..integrations.openai_client import OpenAIClient
from ..utils.logger import get_logger

SIM_PROMPT = """
You are simulating a corporate workshop conversation.

For each question object in the array, produce:
- "response": 2–3 sentence realistic answer from that role (or general audience).
- "score": a float 0.0–1.0 indicating how well the response addresses the question:
  1.0 fully aligned and insightful; 0.5 partially aligned; 0.0 off-topic.

Return STRICT JSON array, mirroring input order, where each item is:
{"response":"...", "score":0.0}
"""

class ConversationSimulator:
    def __init__(self):
        self.ai = OpenAIClient()
        self.logger = get_logger("workshop.sim")

    def simulate(self, company_ctx: Dict, questions: List[Dict]):
        prompt = SIM_PROMPT + "\\n\\nCompany Context:\\n" + json.dumps(company_ctx, ensure_ascii=False) + \
                 "\\n\\nQuestions:\\n" + json.dumps(questions, ensure_ascii=False)
        raw = self.ai.complete_json(prompt, temperature=0.2)
        a = raw.find("["); b = raw.rfind("]")+1
        if a!=-1 and b!=-1: raw = raw[a:b]
        try:
            arr = json.loads(raw)
        except Exception:
            arr = [{"response":"(offline) constructive discussion noted.","score":0.6} for _ in questions]
        return arr
