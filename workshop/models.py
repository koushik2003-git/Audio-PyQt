
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict

Role = str

class Person(BaseModel):
    name: str
    email: EmailStr
    role: Role

class CompanyIntel(BaseModel):
    latest: Optional[str] = None
    financial: Optional[str] = None
    competitors: Optional[str] = None
    extras: List[str] = Field(default_factory=list)

class Company(BaseModel):
    name: str = "Acme Inc."
    company_type: str = "General"
    purpose: str = ""
    key_info: List[str] = Field(default_factory=list)
    objectives: List[str] = Field(default_factory=list)
    intel: CompanyIntel = Field(default_factory=CompanyIntel)
    people: List[Person] = Field(default_factory=list)

class Question(BaseModel):
    id: str
    category: str
    text: str
    role: Optional[str] = None
    score: float = 0.0
    response: str = ""
    notes: Optional[str] = ""

    def dict_for_export(self) -> Dict:
        return {
            "id": self.id,
            "category": self.category,
            "text": self.text,
            "role": self.role,
            "score": self.score,
            "response": self.response,
            "notes": self.notes,
        }

class QuestionSet(BaseModel):
    questions: Dict[str, Question] = Field(default_factory=dict)
    approved: bool = False

class AppConfig(BaseModel):
    openai_model_gpt: str = "gpt-4o"
    openai_model_lite: str = "gpt-4o-mini"
