# GCP Bill of Materials (BOM) — Logical Components

> Source: IBM · Multi-Agent Systems Reference Architecture → `09 BOM & Volumetrics → A. BOM → Azure / AWS / GCP / IBM` (GCP tab).
> Page title: **"GCP Bill of Materials — Logical Components"** — "Recommended GCP services for each logical layer of the L3 component architecture."
> Related: `01_Architecture_Overview.md`, `02_L3_GCP_Component_Overview.md`.
> Note: the "Logical → Physical Component Mapping" table in the source screenshot is cut off at the bottom (last visible row: Code Execution Sandbox). Rows below the cut-off are not captured.

---

## 1. Recommended GCP services per logical layer

| Layer | Logical components (representative) | Recommended GCP service(s) |
|---|---|---|
| Users | External, Enterprise & IT Users | Identity Platform, Cloud Identity |
| Engagement — Channels | Web, Mobile, Voice, Co-pilot Chat | Firebase Hosting, Firebase Cloud Messaging, Speech-to-Text/TTS, Vertex AI Agent Builder |
| Engagement — Business Process | Process Engineering, Finance/Supply Chain/HR Transformation, BPM, RPA | Cloud Workflows, Application Integration, Looker |
| Agentic Framework | Coding Agent, Orchestration, Planning, Reasoning, Reflection, Skills, HITL | Gemini Code Assist, Vertex AI Agent Builder, Vertex AI (Gemini), Workflows + Pub/Sub (HITL) |
| Tool & Integration | MCP Connectors, A2A Protocol, API Gateway, Tool Registry, Sandbox | Cloud Run (MCP/A2A), Apigee, Apigee API Hub, Vertex AI Code Interpreter |
| Knowledge & Memory | Context Engineering, Session Memory, Long-Term Memory, RAG | Memorystore, Firestore, Vertex AI Search / Vector Search |
| AI Model | Code Gen, GenAI, Classical ML, Model Gateway, Guardrails | Gemini Code Assist, Vertex AI (Gemini), Vertex AI AutoML, Vertex AI Safety Filters |
| Enterprise Data & Systems | RDBMS, NoSQL, Knowledge Graph, Vector DB, ERP/CRM/ITSM, Data Lake | Cloud SQL/AlloyDB, Firestore, Spanner Graph, Vertex AI Vector Search, SAP on GCP, GCS + BigQuery |
| Infra / Deployment | Compute, Orchestration, Multi/Hybrid Cloud | Google Kubernetes Engine, Cloud Run, Cloud Functions, Google Distributed Cloud |
| Security & Governance | Auth, Data/Model/Network/Perimeter Security, RBAC, FinOps, Guardrails | Cloud Identity, Cloud KMS, Sensitive Data Protection, Cloud Armor, Cloud Billing, Vertex AI Safety Filters |

---

## 2. Logical → Physical Component Mapping (GCP)

"Each logical component mapped to its physical GCP realization. Items without a direct managed-service equivalent are custom-built."

### Table A (left)
| Logical component | Physical GCP component |
|---|---|
| Web Browsers | Firebase Hosting / Cloud CDN |
| Mobile Applications | Firebase Cloud Messaging |
| Voice Interaction | Speech-to-Text / Text-to-Speech |
| Co-pilot Chat | Vertex AI Agent Builder |
| BPM / RPA | Cloud Workflows / App Integration |
| Coding Agent | Gemini Code Assist |
| Agent Orchestration | Vertex AI Agent Builder / Agent Engine |
| Task Decomposition & Planning | Agent Builder Planner (custom) |
| Reasoning & Action | Vertex AI (Gemini models) |
| Skill Mgmt / HITL Gateway | Agent Tools / Workflows + Pub/Sub |
| Model-Tool Connectors (MCP) | Custom MCP server (Cloud Run) |
| A2A Protocol | Custom (Cloud Run + Apigee) |
| API Gateway / Tool Registry | Apigee / Apigee API Hub |
| Code Execution Sandbox | Cloud Run / Vertex AI Code Interpreter |

### Table B (right)
| Logical component | Physical GCP component |
|---|---|
| Short-Term Session Memory | Memorystore (Redis) |
| Long-Term Knowledge Memory | Firestore |
| Vector DB / RAG Pipeline | Vertex AI Search / Vector Search |
| Code Generation Models | Gemini Code Assist |
| Generative AI Model | Vertex AI (Gemini) |
| Classical ML Model | Vertex AI AutoML / Custom Training |
| Foundation Model Gateway | Vertex AI Model Garden |
| Guardrail & Routing | Vertex AI Safety Filters + Apigee |
| RDBMS / No-SQL | Cloud SQL/AlloyDB / Firestore |
| Knowledge Graph / Vector DB | Spanner Graph / Vector Search |
| ERP / CRM / ITSM | SAP / Salesforce on GCP |
| Data Lake / Warehouse | Cloud Storage + BigQuery |
| Deployment Layer | GKE / Cloud Run / Distributed Cloud |
| Security & Governance | Cloud Identity, KMS, DLP |

(The screenshot table ends at "Security & Governance → Cloud Identity, KMS, DLP"; the Code Execution Sandbox row is the last row visible in Table A.)

---

## 3. Notes for BOM / cost-estimation use
- **Fixed (always-on) infra candidates** — services billed per instance/hour: GKE, Cloud Run (min instances), Cloud SQL/AlloyDB, Spanner, Memorystore (Redis), Apigee, Vertex AI Vector Search (deployed index endpoint), Composer.
- **Variable (usage-based) candidates** — billed by calls/tokens/volume: Vertex AI (Gemini) tokens, Speech-to-Text/TTS, Dialogflow CX, Document AI, Cloud Functions, Pub/Sub, Firestore, BigQuery, Cloud Storage, Firebase Cloud Messaging.
- Items "without a direct managed-service equivalent" are custom-built (e.g. MCP server, A2A protocol, Agent Builder planner).
- Layer names in the BOM table map 1:1 to the L2 layers in `01_Architecture_Overview.md` (the BOM uses "Agentic Framework" for Agentic Orchestration and "Infra / Deployment" for Deployment Layer).
- Environment convention for the downstream agent: default 4 environments — **DEV, SIT, PROD** and one more (user's note lists "DEV, SIT, Prod" as the defaults); quantity should be provided per environment.

---

## 4. Project context captured from the supplementary screenshots (use-case notes)

These two extra screenshots in the folder describe the downstream **BOM-generation tool** this knowledge base feeds.

### 4.1 Agent flow design (hand-drawn diagram)
- **Agent (LangGraph / LangChain)** at the center.
- **Knowledge Base** (BOM, L3 Components Overview, GCP L3 Implementation): the agent reads the reference architecture — L3 architecture components, the L3 GCP implementation overview, and the GCP BOM ("Bill of Materials – Logical Components: recommended GCP services for each logical layer of the L3 component architecture").
- **LLM**: using the knowledge-base information and the user requirement, a **predefined prompt** asks the LLM for the *fixed-component* requirements, expected as **JSON** with: service name, SKU/tier, region, base quantity per environment (default 4 envs: DEV, SIT, Prod …). Non-functional requirements (NFR) are **not** included in this phase; they will be added in a second phase.
- **GCP real-time service cost mapping API**: finds the real-time cost of each fixed-infra service and computes the **total fixed infrastructure cost**.
- **HTML page** output: answer in tabular form in HTML, **also with a downloadable CSV option**.

### 4.2 Reference BOM tool UI ("agentic-bom-volumetrics.html")
- Top controls: Hyperscaler (e.g. Azure), Region (e.g. eastus), Hours/month (730), Pricing proxy URL (optional live prices for non-Azure), **Fetch live prices**, **Export CSV**, **Reset**.
- **1. Inputs** — "Use case + non-functional requirements; choose the hyperscaler above":
  - Use case (example: "Build a customer support agent to know the order status.")
  - Non-functional requirements (availability, latency, throughput, peak factor, RTO/RPO, security, compliance, data residency, retention, DR) (example: "Daily 1 lakh users and response time should be less than 2 secs")
  - LLM API format (OpenAI-compatible), Endpoint URL, Model/deployment (gpt-4o), API key (kept in memory only, never saved)
  - Button: **Design & build BOM**. The design is an LLM proposal; the BOM tables can be edited and costs recalculate.
- **Fixed components** table — "Always-on infra: cost = instances × hours × unit price/hr": columns Component, Instances, Price/hr ($), Source, Monthly ($); with "+ Add component" and a Fixed subtotal.
- **Variable components** table — "Usage-based: monthly volumes and unit prices": columns Component, API calls/mo, Input tokens/mo, Output tokens/mo, $/1K calls, $/1M in tokens, $/1M out tokens, Source, Monthly ($).
