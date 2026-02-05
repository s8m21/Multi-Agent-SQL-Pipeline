import re
import logging
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.utilities import SQLDatabase
from langchain_core.language_models import BaseLanguageModel
from pipelines.staffconnect_chat_files.base_agent import BaseAgent
from pipelines.common_files.llm_utils import extract_json_from_markdown
from pipelines.common_files.sql_utils import execute_sql_safe
from pipelines.common_files.viz_utils import get_unique_filename, python_repl, save_rows_to_csv

TREND_SQL_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are an expert Oracle SQL and visualization assistant.

## Task
Given a user's trend-related question, generate:
1. A valid SQL query.
2. Python matplotlib code (using variable `df`).
3. A brief explanation.

### Output Contract
Return a JSON dictionary with keys: `sql_query`, `python_code`, `explanation`.
No markdown blocks, no commentary.
"""
    ),
    MessagesPlaceholder(variable_name="messages")
])

class TrendAgent(BaseAgent):
    def __init__(self, llm: BaseLanguageModel, db: SQLDatabase):
        super().__init__(llm, db, "Trend")
        self.chain = TREND_SQL_GENERATION_PROMPT | self.llm

    def run(self, question: str, history: List[Dict[str, str]] = []) -> Dict[str, Any]:
        try:
            messages = history + [{"role": "user", "content": question}]
            response = self.chain.invoke({"messages": messages})
            parsed = extract_json_from_markdown(response.content)

            sql_query = parsed.get("sql_query", "").strip()
            python_code = parsed.get("python_code", "")
            explanation = parsed.get("explanation", "")

            # Execute SQL
            headers, rows, error = execute_sql_safe(self.db, sql_query)
            if error:
                return {"error": f"SQL failed: {error}", "sql_query": sql_query}

            # Visualization logic
            csv_filename = save_rows_to_csv(rows, headers)
            chart_filename = get_unique_filename.invoke({"a": 0})

            data_injection = f"import pandas as pd\ndf = pd.read_csv(r'{csv_filename}')\n"
            cleanup = f"\nimport os\nos.remove(r'{csv_filename}')"
            
            chart_response = python_repl.invoke({
                "code": data_injection + python_code + cleanup,
                "sql_query": sql_query,
                "filename": chart_filename
            })

            return {
                "agent": self.name.lower(),
                "sql_query": sql_query,
                "headers": headers,
                "rows": rows,
                "chart_filename": chart_filename,
                "explanation": explanation
            }

        except Exception as e:
            self.logger.error(f"Trend Agent error: {e}")
            return {"error": str(e)}

def build_trend_agent(llm: BaseLanguageModel, db: SQLDatabase):
    agent = TrendAgent(llm, db)
    return agent.run