import re
import logging
from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.utilities import SQLDatabase
from langchain_core.language_models import BaseLanguageModel
from pipelines.staffconnect_chat_files.base_agent import BaseAgent

AUDITTRAIL_SQL_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are an expert Oracle SQL assistant specialized in the StaffConnect system.
You generate **syntactically correct Oracle SQL queries** for the following tables:

1. AuditTrail - user/system activity log (ACTIONTYPEID, USERID, ACTIONTIMESTAMP, SUCCESSFLAG, etc.)
2. Master_ActionType - action type master (ACTIONTYPEID, ACTIONTYPECODE, ACTIONTYPENAME, etc.)
3. Users - user directory (USERID, LOGIN, FULLNAME/NAME, ROLEID, etc.)
4. Master_Role - role master (ROLEID, ROLENAME, etc.)

Your objective:
- Generate a **single valid Oracle SQL query** that answers the user's question about employee actions, login/logout activity, role-based summaries, or AuditTrail events.
- **Do NOT** handle visualizations, trends, or charts.

### Golden Rules
- Use only the listed tables.
- Verify column names — do not invent fields.
- Quote reserved identifiers like "USER" or "TIMESTAMP".
- Prefer sargable filters.
- Join relationships:
    • AuditTrail.ACTIONTYPEID = Master_ActionType.ACTIONTYPEID
    • AuditTrail.USERID = Users.USERID
    • Users.ROLEID = Master_Role.ROLEID
- Login/logout: filter on ACTIONTYPECODE IN ('LOGIN','LOGINASEMPLOYEE','LOGOUT')

### Output Contract
- Return exactly ONE valid Oracle SQL query.
- No semicolon, markdown, or commentary.
"""
    ),
    MessagesPlaceholder(variable_name="messages")
])

class AuditTrailAgent(BaseAgent):
    def __init__(self, llm: BaseLanguageModel, db: SQLDatabase):
        super().__init__(llm, db, "AuditTrail")
        self.chain = AUDITTRAIL_SQL_GENERATION_PROMPT | self.llm

    def run(self, question: str, history: List[Dict[str, str]] = []) -> Dict[str, Any]:
        try:
            messages = history + [{"role": "user", "content": question}]
            response = self.chain.invoke({"messages": messages})
            sql_query = response.content.replace('\n', ' ').strip()
            
            # Use base class helper for execution
            return self._execute_query(sql_query)

        except Exception as e:
            self.logger.error(f"AuditTrail Agent error: {e}")
            return {"error": str(e)}

def build_audittrail_agent(llm: BaseLanguageModel, db: SQLDatabase):
    agent = AuditTrailAgent(llm, db)
    return agent.run
