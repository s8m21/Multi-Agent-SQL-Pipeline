import logging
from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, StateGraph
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_core.language_models import BaseLanguageModel

from pipelines.staffconnect_chat_files.router_agent import build_router_executor
from pipelines.staffconnect_chat_files.audittrail_agent import build_audittrail_agent
from pipelines.staffconnect_chat_files.elmah_error_agent import build_elmah_agent
from pipelines.staffconnect_chat_files.trend_agent import build_trend_agent
from pipelines.staffconnect_chat_files.anomaly_agent import build_anomaly_agent

# Defining agent state schema
from typing import TypedDict, Union

class AgentState(TypedDict):
    question: str
    route: Union[str, None]
    response: Union[str, None]


def create_staffconnect_chain(llm: BaseLanguageModel, db: SQLDatabase):
    """
    Main LangGraph pipeline for StaffConnect chatbot.
    Routes queries based on semantic type: audittrail, elmah, trend, anomaly.
    """

    # Building agents
    audit_agent = build_audittrail_agent(llm, db)
    elmah_agent = build_elmah_agent(llm, db)
    trend_agent = build_trend_agent(llm, db)
    anomaly_agent = build_anomaly_agent(llm, db)

    # Building the router
    router_executor = build_router_executor(llm, db)

    def route(state: AgentState):
        # Using router to classify question
        try:
            router_output = router_executor["router"].invoke({"question": state["question"]})
            route_str = router_output.get("route", None)
            if route_str:
                route_str = route_str.strip().lower()
            logging.info(f"[Router] Routed to: {route_str}")
            return {"route": route_str}
        except Exception as e:
            logging.error(f"[Router] Error during routing: {e}")
            return {"route": None}

    # Agent dispatch functions
    def call_audittrail_agent(state: AgentState):
        return {"response": audit_agent(state["question"])}

    def call_elmah_agent(state: AgentState):
        return {"response": elmah_agent(state["question"])}

    def call_trend_agent(state: AgentState):
        return {"response": trend_agent(state["question"])}

    def call_anomaly_agent(state: AgentState):
        return {"response": anomaly_agent(state["question"])}

    # Building LangGraph
    builder = StateGraph(AgentState)

    builder.add_node("router", RunnableLambda(route))
    builder.set_entry_point("router")

    builder.add_node("audittrail_agent", RunnableLambda(call_audittrail_agent))
    builder.add_node("elmah_agent", RunnableLambda(call_elmah_agent))
    builder.add_node("trend_agent", RunnableLambda(call_trend_agent))
    builder.add_node("anomaly_agent", RunnableLambda(call_anomaly_agent))

    builder.add_edge("audittrail_agent", END)
    builder.add_edge("elmah_agent", END)
    builder.add_edge("trend_agent", END)
    builder.add_edge("anomaly_agent", END)

    builder.add_conditional_edges(
        "router",
        lambda state: state["route"],
        {
            "audittrail": "audittrail_agent",
            "elmah": "elmah_agent",
            "trend": "trend_agent",
            "anomaly": "anomaly_agent",
        }
    )

    graph = builder.compile()
    return graph
