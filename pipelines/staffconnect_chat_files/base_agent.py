from abc import ABC, abstractmethod
import logging
import re
from typing import List, Dict, Any, Union
from langchain_core.language_models import BaseLanguageModel
from langchain_community.utilities import SQLDatabase
from pipelines.common_files.sql_utils import execute_sql_safe

class BaseAgent(ABC):
    def __init__(self, llm: BaseLanguageModel, db: SQLDatabase, name: str):
        self.llm = llm
        self.db = db
        self.name = name
        self.logger = logging.getLogger(name)

    @abstractmethod
    def run(self, question: str, history: List[Dict[str, str]] = []) -> Dict[str, Any]:
        """Entry point for the agent logic."""
        pass

    def _execute_query(self, sql_query: str) -> Dict[str, Any]:
        """Standard execution wrapper."""
        sql_query = re.sub(r'\s+', ' ', sql_query).strip()
        headers, rows, error = execute_sql_safe(self.db, sql_query)
        
        if error:
            self.logger.error(f"SQL execution failed: {error}")
            return {"error": f"SQL execution failed: {error}", "sql_query": sql_query}

        return {
            "agent": self.name.lower(),
            "sql_query": sql_query,
            "headers": headers,
            "rows": rows,
        }
