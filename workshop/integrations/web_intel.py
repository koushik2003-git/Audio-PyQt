
from .integrations.openai_client import OpenAIClient
from .utils.logger import get_logger

LATEST_PROMPT = """
Summarize the most recent public updates for the company below:
Company: {company_name}
Type/Industry: {company_type}
Return a crisp paragraph (80–140 words) with dates if obvious, focusing on news, leadership, product, partnerships, and strategy.
"""

FINANCIAL_PROMPT = """
Provide a financial-style snapshot (80–140 words) for the company below. If the firm is private, infer sensibly from typical narratives.
Company: {company_name}
Type/Industry: {company_type}
Include revenue trend, margins, cost pressures, major investments, and any capital/partnership notes.
"""

COMPETITOR_PROMPT = """
List the 3–5 most relevant competitors for the company below and one sentence on how our company differentiates.
Company: {company_name}
Type/Industry: {company_type}
Return as a short paragraph.
"""

class WebIntel:
    def __init__(self):
        self.ai = OpenAIClient()
        self.logger = get_logger("workshop.webintel")

    def fetch_latest(self, company_name: str, company_type: str) -> str:
        return self.ai.complete_text(LATEST_PROMPT.format(company_name=company_name or "the company",
                                                         company_type=company_type or "industry"))

    def fetch_financial(self, company_name: str, company_type: str) -> str:
        return self.ai.complete_text(FINANCIAL_PROMPT.format(company_name=company_name or "the company",
                                                             company_type=company_type or "industry"))

    def fetch_competitors(self, company_name: str, company_type: str) -> str:
        return self.ai.complete_text(COMPETITOR_PROMPT.format(company_name=company_name or "the company",
                                                              company_type=company_type or "industry"))
