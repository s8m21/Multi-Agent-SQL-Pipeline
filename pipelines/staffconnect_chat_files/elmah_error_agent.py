import re
import logging
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.utilities import SQLDatabase
from langchain_core.language_models import BaseLanguageModel
from pipelines.staffconnect_chat_files.base_agent import BaseAgent

ELMAH_SQL_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are an expert Oracle SQL assistant focused on analyzing application exceptions using ELMAH logs.

You ONLY have access to the following table:
- **ELMAH_Error** (ErrorId, Application, Host, Type, Source, Message, User, StatusCode, TimeUtc, AllXml, Sequence, etc.)

### Your Job
- Generate ONE valid Oracle SQL query for the user's question about exceptions.
- Do NOT generate explanations, charts, or visualizations.
- No semicolon, no markdown, no commentary.
"""
    ),
    MessagesPlaceholder(variable_name="messages")
])

class ElmahErrorAgent(BaseAgent):
    def __init__(self, llm: BaseLanguageModel, db: SQLDatabase):
        super().__init__(llm, db, "Elmah")
        self.chain = ELMAH_SQL_GENERATION_PROMPT | self.llm

    def run(self, question: str, history: List[Dict[str, str]] = []) -> Dict[str, Any]:
        try:
            messages = history + [{"role": "user", "content": question}]
            response = self.chain.invoke({"messages": messages})
            sql_query = response.content.replace('\n', ' ').strip()
            
            return self._execute_query(sql_query)

        except Exception as e:
            self.logger.error(f"ELMAH Agent error: {e}")
            return {"error": str(e)}

def build_elmah_agent(llm: BaseLanguageModel, db: SQLDatabase):
    agent = ElmahErrorAgent(llm, db)
    return agent.run
