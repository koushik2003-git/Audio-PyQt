
import json
import uuid
from typing import Dict, List, Any
from ..models import Company, Question, QuestionSet
from ..integrations.openai_client import OpenAIClient
from ..utils.logger import get_logger

QUESTION_GEN_PROMPT = """
You are an expert corporate workshop facilitator. Generate 10–14 questions.
Return STRICT JSON array where each item has fields:
  {{"category": "Strategy|Operations|Risk|Finance|People|Technology",
    "role": "<role or null>",
    "text": "<question text>"}}

Context:
Company: {company_name} ({company_type})
Purpose: {purpose}

Key Info (bulleted):
{key_info}

Objectives (bulleted):
{objectives}

Desired Nature of Questions:
{nature}
"""

REGEN_FROM_NOTES_PROMPT = """
You are improving the existing questions using the facilitator's notes. Return a new JSON array with the same format as before.
Notes:
{notes}

Keep the audience roles and categories balanced. Remove duplicates, ensure clarity.
"""

class GPTQuestionGenerator:
    def __init__(self):
        self.ai = OpenAIClient()
        self.logger = get_logger("workshop.qgen")

    def _coerce_items(self, data: Any) -> List[dict]:
        if isinstance(data, dict):
            for k in ("items","questions","data"):
                if isinstance(data.get(k), list):
                    data = data[k]
                    break
        if not isinstance(data, list):
            return []
        out: List[dict] = []
        for it in data:
            if isinstance(it, dict):
                out.append({"category": it.get("category","General"),
                            "role": it.get("role"),
                            "text": (it.get("text","") or "").strip() or "(blank)"})
            elif isinstance(it, str):
                out.append({"category":"General","role":None,"text":it.strip()})
            else:
                out.append({"category":"General","role":None,"text":str(it)})
        return out

    def _json_loads(self, text: str):
        a = text.find("["); b = text.rfind("]")+1
        if a!=-1 and b!=-1: text = text[a:b]
        else:
            a = text.find("{"); b = text.rfind("}")+1
            if a!=-1 and b!=-1: text = text[a:b]
        try:
            return json.loads(text)
        except Exception:
            return ["What are the top priorities for the next 12 months?"]

    def generate(self, company: Company, question_nature: str) -> QuestionSet:
        payload = QUESTION_GEN_PROMPT.format(
            company_name=company.name,
            company_type=company.company_type,
            purpose=company.purpose,
            key_info="; ".join(company.key_info) or "-",
            objectives="; ".join(company.objectives) or "-",
            nature=question_nature.strip() or "Strategic alignment, outcomes, risks, feasibility, and change management."
        )
        raw = self.ai.complete_json(payload, model=None, temperature=0.3)
        data = self._json_loads(raw)
        items = self._coerce_items(data)
        qs: Dict[str, Question] = {}
        for item in items:
            q = Question(id=str(uuid.uuid4())[:8],
                         category=item.get("category","General"),
                         role=item.get("role"),
                         text=item.get("text","").strip(),
                         score=0.0, response="", notes="")
            qs[q.id] = q
        return QuestionSet(questions=qs, approved=False)

    def regenerate_from_notes(self, company: Company, question_nature: str, questions_with_notes: list) -> QuestionSet:
        notes_blob = "\\n".join([f"- {q['notes']}" for q in questions_with_notes if q.get('notes')])
        payload = REGEN_FROM_NOTES_PROMPT.format(notes=notes_blob or "No notes provided.")
        raw = self.ai.complete_json(payload, model=None, temperature=0.3)
        data = self._json_loads(raw)
        items = self._coerce_items(data)
        qs: Dict[str, Question] = {}
        for item in items:
            q = Question(id=str(uuid.uuid4())[:8],
                         category=item.get("category","General"),
                         role=item.get("role"),
                         text=item.get("text","").strip(),
                         score=0.0, response="", notes="")
            qs[q.id] = q
        return QuestionSet(questions=qs, approved=False)
