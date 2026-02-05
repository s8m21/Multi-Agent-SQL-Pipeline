# StaffConnect: Multi-Agent SQL Analytics Pipeline (Open WebUI + LangGraph)

A professional-grade, agentic blueprint for enterprise-level **Text-to-SQL** analytics, built on the **Open WebUI Pipelines** framework. This system uses **LangGraph** to orchestrate specialized LLM agents that generate safe SQL, query an Oracle database, run higher-level analytics (trends/anomalies), and return a **structured response** with optional **matplotlib visualizations**.

> **Architecture Overview**
- **Host Framework**: [Open WebUI Pipelines](https://github.com/open-webui/pipelines)
- **Orchestration**: LangGraph (Router → Experts → Aggregation)
- **Pipeline Type**: Manifold (Exposes multiple model IDs like `gpt-4o-mini`, `o3-mini`)
- **Database**: Agnostic (Oracle, PostgreSQL, SQL Server via SQLAlchemy)

> **Who this is for**
- AI Engineers building **agentic analytics** over enterprise databases
- Data/Platform teams that want a modular Text-to-SQL stack with guardrails
- Anyone who wants a clean reference architecture for **Router → Experts → Aggregation → Visualization**

---

## Table of Contents
- [Key Concepts](#key-concepts)
- [High-Level Architecture](#high-level-architecture)
- [Repository Layout](#repository-layout)
- [Open WebUI Integration](#open-webui-integration)
- [Execution Flow: What Happens on a Query](#execution-flow-what-happens-on-a-query)
- [Agents](#agents)
- [State Model](#state-model)
- [SQL Safety & Guardrails](#sql-safety--guardrails)
- [Visualization & Output Contracts](#visualization--output-contracts)
- [Configuration](#configuration)
- [Local Setup](#local-setup)
- [Running the App](#running-the-app)
- [Testing](#testing)
- [Docker](#docker)
- [Examples](#examples)
- [Extending the System](#extending-the-system)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Key Concepts

### Open WebUI Manifold Pipeline
This project is implemented as a **Manifold Pipeline**. Unlike a standard pipe, a manifold allows a single backend script to register multiple models in the Open WebUI interface. In this case, it exposes different LLM "brains" for the same SQL analytics engine.

### Router-Expert Pattern
The system uses a **Router** to classify user intent and dispatch the query to one specialized **Expert Agent** (or sometimes multiple, depending on your graph design). Each expert is optimized for a particular domain:
- Audit trail / activity logs
- Error log analysis (ELMAH-style)
- Trends / time-series analytics
- Anomaly detection

### LangGraph as the Orchestrator
LangGraph models the workflow as a **state machine**:
- Each node reads/writes to a shared `AgentState`
- Conditional edges route to the right expert agent
- You can add loops (repair/refine) when SQL fails or outputs are incomplete

---

## High-Level Architecture

```mermaid
graph TD
    UI[Open WebUI Interface] --> Gateway[FastAPI Pipeline Gateway]
    Gateway --> Pipeline[StaffConnect Manifold Pipeline]
    
    subgraph LangGraph Orchestrator
        Pipeline --> Router{Intent Router}
        Router -- "Audit" --> AA[Audit Trail Agent]
        Router -- "Errors" --> EA[ELMAH Agent]
        Router -- "Trends" --> TA[Trend Agent]
        Router -- "Anomaly" --> ANA[Anomaly Agent]
        
        AA & EA & TA & ANA --> Collector[Unified Context Collector]
    end

    Collector --> Viz[Visualization Engine]
    Viz --> UI
```

---

## Repository Layout
Top-level folders and files in this repo: 

```text
.github/                  # CI workflows and repo automation
blueprints/               # Reusable LangGraph blueprints / templates
docs/                     # Documentation notes / design references
examples/                 # Example queries, scripts, or sample runs
pipelines/                # Core agent graph(s) + agent implementations
  staffconnect_chat.py    # Main Open WebUI Pipeline entry point
  staffconnect_chat_files/# Agent logic, chains, and LangGraph definitions
  common_files/           # Modularized utilities (SQL, Viz, LLM, Logging)
tests/                    # Unit/integration tests
utils/pipelines/          # Framework-level helpers (Auth, Misc, Stream)

config.py                 # Central configuration loader (env, flags)
schemas.py                # Pydantic / typed schemas used across agents
main.py                   # Entry point (FastAPI Gateway serving the pipelines)
docker-compose.yaml       # Container orchestration
Dockerfile                # Container build
env.example               # Example env vars
dev.sh / start.sh         # Convenience scripts
CONTRIBUTING.md           # Contribution guide
LICENSE                   # MIT license
```

### Where to start reading the code
If you’re new to the codebase, read in this order:
1. `main.py` → app entry, graph build, execution loop
2. `pipelines/staffconnect_chat.py` → Open WebUI Pipeline entry & Gateway wiring
3. `pipelines/staffconnect_chat_files/` → router + agent nodes + graph wiring
4. `schemas.py` → state + response contracts
5. `pipelines/common_files/` → SQL cleaning, execution, chart creation
6. `tests/` → what “correct behavior” means

---

## Open WebUI Integration

### Valves (Configuration)
Configuration is handled via Open WebUI **Valves**. You can set these directly in the WebUI settings:
- `DATABASE_URL`: Generic SQLAlchemy connection string.
- `OPENAI_API_KEY`: LLM access.
- `CHART_DIRECTORY_STAFFCONNECT`: Path where generated analytic plots are stored.

### Gateway Server
The `main.py` file at the root acts as a standalone FastAPI server that is **OpenAI-API compatible**. You can connect Open WebUI to this gateway to host your custom pipelines.

---

## Execution Flow: What Happens on a Query
This is the conceptual runtime pipeline (matches the repo’s structure and file responsibilities):

1. **User query enters the system**: (CLI loop, API layer in `main.py`, or via Open WebUI).
2. **State is initialized**: (`AgentState`) with raw user input, conversation history (optional), and db connection settings.
3. **Router node runs**: Classifies intent (audit/errors/trends/anomaly/general sql) and writes `state.route = <agent_name>`.
4. **Expert agent runs**: Loads schema context, generates SQL or analysis plan, executes SQL safely, and returns structured data + explanation.
5. **Collector node aggregates**: Normalizes outputs into one common contract and attaches metadata (timing, rows, warnings).
6. **Visualization node optionally runs**: If agent output requests a plot (or data looks plottable), it creates chart images / base64 payload.
7. **Final formatter returns**: human-readable answer + machine-readable JSON payload + optional chart payload.

---

## Agents
This repo’s modular design supports 4 core expert agents.

### 1) Audit Trail Agent
**Intent**: audit/activity investigation
Typical outputs:
- top events by user/action/time window
- suspicious access patterns
- drill-down by entity IDs

### 2) ELMAH Agent
**Intent**: error logs / failures / stack traces
Typical outputs:
- error frequency trends
- top exception types + root cause hints
- correlation with deployments/time windows

### 3) Trend Agent
**Intent**: time-series / KPI style analytics
Typical outputs:
- daily/weekly aggregation
- moving averages
- seasonality hints
- plot-ready series

### 4) Anomaly Agent
**Intent**: detecting outliers
Typical outputs:
- z-score/IQR based outliers
- abrupt shifts
- rare event spikes
- “why flagged” explanations

**Implementation note (recommended pattern)**
Each agent should implement a consistent interface like `run(state: AgentState) -> AgentState` or `invoke(state) -> dict` then merged into state. Refer to `BaseAgent` in `pipelines/staffconnect_chat_files/base_agent.py`.

---

## State Model
State is the backbone of LangGraph workflows. Refer to `schemas.py` for the actual schema.

### Recommended AgentState fields
- `query`: User input
- `route`: Router decision
- `messages`: Conversation history (optional)
- `sql`: Generated SQL
- `params`: Bound parameters (if supported)
- `rows`: Query results (normalized)
- `analysis`: Computed analytics (trend/anomaly)
- `chart`: Chart payload (path/base64/bytes)
- `errors`: Error stack / LLM failures
- `warnings`: Safety filters triggered
- `metadata`: Timing, rowcount, tokens, model name, etc.

---

## SQL Safety & Guardrails
Text-to-SQL systems fail in predictable ways; this repo includes tests aimed at SQL cleaning + LLM parsing. 

### Recommended safety constraints
- **Read-only by default**: allow only `SELECT`.
- **Block keywords**: `DROP`, `TRUNCATE`, `ALTER`, `GRANT`, `REVOKE`, etc.
- **Enforce row limits**: (`FETCH FIRST N ROWS ONLY`).
- **Enforce schema/table allowlist**: (optional).
- **Parameterize values**: whenever possible.
- **Validate against known schema**: (table/column existence).

### Common repair loop
If SQL fails:
1. capture DB error (`ORA-xxxxx`).
2. feed error back to the agent (repair prompt).
3. regenerate SQL with constraints.
4. retry with capped attempts.

---

## Visualization & Output Contracts
### Visualization Engine
- Agent returns data + suggested plot type (line/bar/hist).
- Viz layer generates matplotlib chart.
- Chart is returned inline (base64) or saved to disk (path) depending on configuration in Valves.

### Structured Response
Your final response should be both:
- **Human readable**: explanation + key insights.
- **Machine readable**: JSON including route used, SQL executed, rows summary, chart payload, and warnings/errors.

---

## Configuration

Configuration is centralized in `config.py` and Open WebUI Valves.

### Environment variables (recommended)
```bash
# LLM
OPENAI_API_KEY=...
OPENAI_MODEL=...

# Oracle
ORACLE_HOST=...
ORACLE_PORT=1521
ORACLE_SERVICE=...
ORACLE_USER=...
ORACLE_PASSWORD=...

# Runtime
LOG_LEVEL=INFO
MAX_ROWS=500
SQL_READ_ONLY=true
```
`env.example` is the canonical list—keep it updated as you add features. 

---

## Local Setup
### Requirements
- Python 3.11+
- Oracle Instant Client (needed for `cx_Oracle`/Oracle driver)
- An OpenAI API Key

### Install
```bash
git clone https://github.com/s8m21/Multi-Agent-SQL-Pipeline.git
cd Multi-Agent-SQL-Pipeline
pip install -r requirements.txt
```
### Env Config
```bash
cp env.example .env
# edit .env with your values
```

### Connection String Examples
- **Oracle**: `oracle+cx_oracle://user:password@host:port/?service_name=service`
- **PostgreSQL**: `postgresql://user:password@host:port/dbname`
- **SQL Server**: `mssql+pyodbc://user:password@host:port/dbname?driver=ODBC+Driver+17+for+SQL+Server`

---

## Running the App
### Option A: Pipeline Gateway (Recommended)
```bash
python main.py
```
Add `http://localhost:9099` to Open WebUI as an OpenAI connection.

### Option B: Direct Python Execution
For testing purposes, you can execute individual agent scripts or the main entry.

---

## Testing
A test suite is included in `tests/`. 
```bash
pytest
```
**Focus on**: SQL cleaning functions, Router classification, and Repair loop behavior.

---

## Docker
- **Build**: `docker build -t staffconnect-sql-pipeline .`
- **Compose**: `docker compose up --build`

---

## Examples
Check `examples/` for runnable demo scripts or sample prompts. 
- "Show top 10 users by failed logins last 7 days"
- "Plot error count by day for the last 30 days"

---

## Extending the System
- **Add a Agent**: Create in `pipelines/staffconnect_chat_files/`, implement `run(state)`, and add to Router.
- **Add a Tool**: Place in `pipelines/common_files/` and keep it pure and safe-by-default.

---

## Troubleshooting
- **Oracle client**: Ensure Instant Client is in your PATH.
- **LLM parsing**: Use strict output prompts or JSON repair passes.
- **SQL failures**: Feed ORA-error codes back to the repair loop.

---

## Contributing
See `CONTRIBUTING.md`. 

---

## License
MIT. See `LICENSE`.
