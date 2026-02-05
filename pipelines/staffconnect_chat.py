"""
title: Staff Connect SQL Agent
author: Spandan
date: 2025-10-20
version: 1.0
license: MIT
description: A “manifold” pipeline for text-to-sql agent querying staffconnect (Oracle) database, supporting gpt-4o-mini and o3-mini models.
requirements: aiofiles, langchain_openai, langchain_core, langchain_community, langchain_experimental, langgraph, langgraph-prebuilt, cx_Oracle, sqlalchemy, sqlparse, werkzeug, tiktoken
"""

import os
import json
import base64
import logging
import traceback
from dotenv import load_dotenv
from pydantic import BaseModel
from sqlalchemy import create_engine
from langchain_openai import ChatOpenAI
from werkzeug.utils import secure_filename
from langchain_community.utilities import SQLDatabase
from typing import List, Union, Generator, Iterator, Dict
from pipelines.common_files.logging_utils import OpenObserveHTTPHandler
from pipelines.common_files.ui_utils import format_result_for_ui
from pipelines.staffconnect_chat_files.chains import create_staffconnect_chain


class Pipeline:
    class Valves(BaseModel):
        ORACLE_USER: str = ""
        ORACLE_PASSWORD: str = ""
        ORACLE_HOST: str = ""
        ORACLE_PORT: str = ""
        ORACLE_SERVICE: str = "" 
        OPENAI_API_KEY: str = ""
        CHART_DIRECTORY_STAFFCONNECT: str = "" 
        OPENOBSERVE_HOST: str = ""
        OPENOBSERVE_USERNAME: str = ""
        OPENOBSERVE_PSWD: str = ""

    def __init__(self):
        self.type = "manifold"
        self.name = "Staff Connect AI Agent"  
        load_dotenv(override=True)
        self.valves = self.Valves(**{
            "ORACLE_USER": os.getenv("ORACLE_USER", "").strip('"\''), 
            "ORACLE_PASSWORD": os.getenv("ORACLE_PASSWORD", "").strip('"\''), 
            "ORACLE_HOST": os.getenv("ORACLE_HOST", "").strip('"\''), 
            "ORACLE_PORT": os.getenv("ORACLE_PORT", "1521").strip('"\''), 
            "ORACLE_SERVICE": os.getenv("ORACLE_SERVICE", "").strip('"\''), 
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "").strip('"\''), 
            "CHART_DIRECTORY_STAFFCONNECT": os.getenv("CHART_DIRECTORY_STAFFCONNECT", "").strip('"\''), 
            "OPENOBSERVE_HOST": os.getenv("OPENOBSERVE_HOST", "").strip('"\''), 
            "OPENOBSERVE_USERNAME": os.getenv("OPENOBSERVE_USERNAME", "").strip('"\''), 
            "OPENOBSERVE_PSWD": os.getenv("OPENOBSERVE_PSWD", "").strip('"\''), 
        })
        self.pipelines = self.get_models()
        self._llm_map: Dict[str, Union[ChatOpenAI, None]] = {}
        self._llm_context_lengths: Dict[str, int] = {}

    def get_models(self) -> List[Dict[str, str]]:
        return [
            {"id": "gpt-4o-mini", "name": "gpt-4o-mini"},
            {"id": "o3-mini", "name": "o3-mini"},
        ]

    async def on_startup(self):
        print(f"Pipeline {self.name} starting up…")
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            h = OpenObserveHTTPHandler(
                self.valves.OPENOBSERVE_HOST,
                "/api/default/default/_json",
                self.valves.OPENOBSERVE_USERNAME,
                self.valves.OPENOBSERVE_PSWD,
            )
            h.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(h)
        self.logger = logger

        cd = self.valves.CHART_DIRECTORY_STAFFCONNECT 
        if cd and not os.path.isdir(cd):
            os.makedirs(cd, exist_ok=True)

        oracle_conn_str = (
            "oracle+cx_oracle://{user}:{password}@{host}:{port}/?service_name={service}"
        ).format( 
            user=self.valves.ORACLE_USER,
            password=self.valves.ORACLE_PASSWORD,
            host=self.valves.ORACLE_HOST,
            port=self.valves.ORACLE_PORT,
            service=self.valves.ORACLE_SERVICE
        )
        self.staffconnect_engine = create_engine(oracle_conn_str) 
        self.staffconnect_db = SQLDatabase(self.staffconnect_engine)

        llm_main = None
        llm_context_lengths = {}

        if self.valves.OPENAI_API_KEY:
            os.environ["OPENAI_API_KEY"] = self.valves.OPENAI_API_KEY
            llm_main = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
        if self.valves.OPENAI_API_KEY:
            os.environ["OPENAI_API_KEY"] = self.valves.OPENAI_API_KEY
            llm_o3 = ChatOpenAI(model="o3-mini")

        self._llm_map = {
            "gpt-4o-mini": llm_main,
            "o3-mini": llm_o3,
        }
        self._llm_context_lengths = llm_context_lengths

        # Build the LangGraph multi-agent chain
        self.staffconnect_chain = create_staffconnect_chain(llm_main, self.staffconnect_db)

    async def on_shutdown(self):
        print(f"Pipeline {self.name} shutting down…")

    def pipe(self, user_message: str, model_id: str, messages: List[dict], body: dict) -> Union[str, Iterator, Generator]:
        try:
            if isinstance(body, str):
                body = json.loads(body)
            all_messages = (body or {}).get("messages", messages or [])
            question = user_message

            llm = self._llm_map.get(model_id)
            if llm is None:
                return json.dumps(
                    {
                        "error": f"Model '{model_id}' is not configured. Check your API keys."
                    }
                )

            # Run the LangGraph multi-agent chain
            state = {"question": question, "route": None, "response": None}
            result = self.staffconnect_chain.invoke(state)
            response = result.get("response", {})
            route = result.get("route", "")

            # Embed chart if returned
            filename = response.get("chart_filename") if isinstance(response, dict) else None
            encoded_image = None

            if filename:
                if not filename.lower().endswith(".png"):
                    filename += ".png"
                base_name = os.path.basename(filename)
                safe_name = secure_filename(base_name)
                chart_path = os.path.join(self.valves.CHART_DIRECTORY_STAFFCONNECT, safe_name)
                try:
                    with open(chart_path, "rb") as f:
                        encoded_image = base64.b64encode(f.read()).decode("utf-8")
                except Exception as e:
                    self.logger.error(f"Chart load error: {e}", extra={"custom_job_name": self.name})

            if isinstance(response, dict):
                markdown = format_result_for_ui(response)
                if encoded_image:
                    return f"{markdown}\n\n![image](data:image/png;base64,{encoded_image})"
                return markdown
            elif isinstance(response, str):
                return f"Routed to: `{route}`\n\n{response}"
            else:
                return str(response)
            
        except Exception:
            tb = traceback.format_exc()
            self.logger.error(f"Uncaught exception:\n{tb}",
                              extra={"custom_job_name": self.name})
            return json.dumps({
                "error": "Internal server error. See trace for details.",
                "trace": tb
            })