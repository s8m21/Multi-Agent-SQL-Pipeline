import logging
from typing import Literal, TypedDict
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.utilities import SQLDatabase
from langchain_core.language_models import BaseLanguageModel

from pipelines.staffconnect_chat_files.audittrail_agent import build_audittrail_agent
from pipelines.staffconnect_chat_files.elmah_error_agent import build_elmah_agent
from pipelines.staffconnect_chat_files.trend_agent import build_trend_agent
from pipelines.staffconnect_chat_files.anomaly_agent import build_anomaly_agent

class RouteOutput(TypedDict):
    route: Literal["audittrail", "elmah", "trend", "anomaly"]


def create_router_prompt() -> ChatPromptTemplate:
    system = """You are an intent classifier for a staffconnect application with access to various agents.

Classify the user question into one of the following categories:

- audittrail: questions related to audit trail logs, user activity, login/logout, shift changes.
- elmah: questions about ELMAH error logs, including application errors, API issues, or failed web requests.
- trend: time-based trend or visualization questions (login frequency, error spikes, charts).
- anomaly: questions comparing baseline logs vs current logs for deviations or anomalies.

Respond only with one of the four words: audittrail, elmah, trend, anomaly.

Do not answer the question. Just classify it."""
    return ChatPromptTemplate.from_messages([
        ("system", system),
        ("human", "{question}")
    ])

def create_router(llm: BaseLanguageModel) -> Runnable:
    prompt = create_router_prompt()
    
    def extract_route(output):
        # Handle dict, AIMessage, or plain string
        if isinstance(output, dict):
            text = output.get("content", "")
        elif hasattr(output, "content"):
            text = output.content
        else:
            text = str(output)
        text = text.strip().lower()

        valid_routes = {"audittrail", "elmah", "trend", "anomaly"}
        if text not in valid_routes:
            logging.error(f"[Router] Invalid route returned by LLM: {text}")
            text = "audittrail"

        logging.info(f"[Router] Classified route: {text}")
        return {"route": text}
    
    return prompt | llm | RunnableLambda(extract_route)


def build_router_executor(llm: BaseLanguageModel, db: SQLDatabase) -> Runnable:
    router_chain = create_router(llm)

    destinations = {
        "audittrail": build_audittrail_agent(llm, db),
        "elmah": build_elmah_agent(llm, db),
        "trend": build_trend_agent(llm, db),
        "anomaly": build_anomaly_agent(llm, db),
    }

    return {
        "router": router_chain,
        "destinations": destinations,
    }
