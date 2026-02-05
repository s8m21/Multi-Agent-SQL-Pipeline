import os
import logging
from typing import List, Dict, Any
from langchain_core.language_models import BaseLanguageModel
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate
from pipelines.staffconnect_chat_files.base_agent import BaseAgent

ANOMALY_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     """
You are an expert system administrator and software engineer analyzing ELMAH_ERROR logs.

Baseline Reference: July 2025.
Identify deviations in new logs.

Output: A short, human-readable summary of anomalies, root causes, and recommended actions.
"""),
    ("user", "{input}")
])

class AnomalyAgent(BaseAgent):
    def __init__(self, llm: BaseLanguageModel, db: SQLDatabase):
        super().__init__(llm, db, "Anomaly")
        self.chain = ANOMALY_ANALYSIS_PROMPT | self.llm
        self.memory_summary = self._load_baseline_memory()

    def _load_baseline_memory(self) -> str:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(current_dir, "memory", "elmah_baseline.txt")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return "No baseline found."

    def run(self, question: str, history: List[Dict[str, str]] = []) -> Dict[str, Any]:
        try:
            sql_query = """
SELECT ErrorId, Application, Type, Source, Message, TimeUtc
FROM ELMAH_Error
WHERE TimeUtc >= SYSDATE - 1
ORDER BY TimeUtc DESC
FETCH NEXT 50 ROWS ONLY
"""
            current_logs = self.db.run(sql_query)
            
            full_input = (
                f"Baseline: {self.memory_summary}\n\n"
                f"Current Logs: {current_logs}\n\n"
                f"User Question: {question}"
            )

            response = self.chain.invoke({"input": full_input})
            return {
                "agent": self.name.lower(),
                "sql_query": sql_query,
                "explanation": response.content
            }

        except Exception as e:
            self.logger.error(f"Anomaly Agent error: {e}")
            return {"error": str(e)}

def build_anomaly_agent(llm: BaseLanguageModel, db: SQLDatabase):
    agent = AnomalyAgent(llm, db)
    return agent.run
