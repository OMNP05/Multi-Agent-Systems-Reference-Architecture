# L3 Component Overview — GCP View

> Source: IBM · Multi-Agent Systems Reference Architecture → `04 Architecture → C. L3 Component Overview`, with **Cloud Platform = GCP** selected. Drill-down pages per layer are captured as well.
> Page title: **"L3 Component Overview — Layer, Purpose & Key Technologies"** — "Detailed component breakdown of the platform, from user layer through infrastructure, with security & governance as cross-cutting concerns."
> View selector: `Generic (Logical)` · `Azure` · **`GCP`** · `AWS` · `IBM` · `IBM Enterprise Advantage`
> Related: `01_Architecture_Overview.md` (layers), `03_GCP_BOM.md` (logical→physical mapping).

Notation: **Component** — sub-label (role). Each card has an "i" tooltip in the UI.

---

## 1. USERS group

### Layer: User
*Purpose:* Represent all human and system consumers interacting with the platform.

| Component | Role / maps to |
|---|---|
| External Users | → Firebase Auth (Identity Platform). Examples: Customer, Suppliers, Others |
| Enterprise Users | → Cloud Identity + Workforce IDP + IAP. Examples: Marketing, Finance, HR |
| IT Users | → Cloud Identity + IAM. Examples: Engineers, Supports, Others |
| Others | (generic bucket) |

**Interaction sequence — end-to-end user interaction flow** (human and system actors authenticating, submitting intents via channels, receiving governed multi-agent responses). Participants: Enterprise User (Human Actor), Firebase / Cloud ID (Users Layer – Auth), Dialogflow / Run (Channels Layer), Vertex Agent Bldr (Agentic Layer), Safety Filters/IAM (Security & Gov).
1. Authenticate with credentials / SSO (User → Firebase/Cloud ID)
2. Issue secure identity token & RBAC roles (response)
3. Submit prompt / request with user context (User → Dialogflow/Run)
4. Validate caller identity & entitlements (Channels → Safety Filters/IAM)
5. Dispatch authenticated intent to agent pipeline (Safety/IAM → Vertex Agent Builder)
6. Return generated plan & agent execution result (response to Channels)
7. Render response in digital workspace / copilot (response to User)

---

## 2. ENGAGEMENT group

### Layer: Channels
*Purpose:* Provide the digital and conversational channels through which users interact with the platform.

| Component | Sub-label |
|---|---|
| Firebase Hosting | Web channel (tooltip: global CDN-backed static hosting with one-command deploys, SSL, and preview channels) |
| Firebase Cloud Messaging | Mobile push |
| Cloud Run | Container-based channel |
| Dialogflow CX | Voice Interaction |
| CCAI | Co-pilot Chat |
| Speech-to-Text / TTS | Voice |
| Vertex AI Agent Builder | Co-pilot builder |

**Interaction sequence — omnichannel ingestion & streaming flow** (digital channels capture speech/text inputs, enforce rate-limits, stream agent actions back). Participants: Users Layer (Cloud Identity Users), Firebase / Run, Dialogflow / TTS (both Channels Component), Cloud Workflows (Business Process Layer), Vertex Agent Bldr (Agentic Solution Layer).
1. Initiate interaction / chat conversation
2. Transcribe voice stream to text prompt (if audio)
3. Trigger associated business workflow / case
4. Invoke autonomous agent for dynamic reasoning
5. Stream incremental thoughts and tool status (response)
6. Live update interactive UI with final output (response)

### Layer: Business Process – Workflows & Applications
*Purpose:* Orchestrate business processes, workflows, and enterprise application integrations.

| Component | Sub-label |
|---|---|
| Cloud Workflows | Process Engineering / BPM |
| Composer | Workflow orchestration (tooltip: managed Apache Airflow service for authoring, scheduling and monitoring complex data and ML pipelines) |
| Looker (Finance) | Finance Transformation |
| Document AI | Document Processing |
| Workday on GCP | HR & Talent |
| Cloud Workflows | BPM |
| App Integration | RPA |

**Interaction sequence — business process orchestration & human escalation flow** (enterprise workflows delegating sub-tasks to agents, handling HITL review gates, executing RPA tasks). Participants: Channels Layer (Dialogflow / Run), Cloud Workflows, Composer / App Int. (Biz Process Components), Vertex Agent Bldr (Agentic Solution Layer), Data & Systems (BigQuery / Cloud SQL / SAP).
1. Trigger multi-step business process instance
2. Dispatch complex analytical step to agent
3. Return agent recommendation & confidence score (response)
4. Trigger automated RPA / system update task
5. Update records of truth in ERP / CRM backend
6. Confirm transactional commit status (response)

---

## 3. MULTI-AGENT SOLUTION group (dashed boundary)

### Layer: Agentic Orchestration
*Purpose:* Plan, reason and orchestrate autonomous agent behavior including task decomposition, skill management and human-in-the-loop checkpoints.

**Coding Plane** (core engineering components for building & maintaining agents)

| Category | Component | Sub-label |
|---|---|---|
| Coding Plane | Gemini Code Assist | Coding Agent |
| Coding Plane | Agent Studio | Agent Orchestration |
| Coding Plane | Vertex AI Agent Builder | Agent build |
| Capability | Agent Builder (Planner/Reflection) | Task Decomposition |
| Capability | Vertex AI (Gemini) | Reasoning & Action |
| Capability | Gen AI Eval Service | Reflection |
| Capability | Agent Tools/Extensions | Skill Management |
| Capability | Workflows + Firestore + Pub/Sub | HITL Gateway |

**Interaction sequence — autonomous agent reasoning, reflection & execution loop** (orchestrator decomposes goals, invokes foundation models, consults memory, delegates tools). Participants: Vertex Agent Bldr (Agentic Core Component), Workflows / PubSub (HITL Gateway & Eval), Vertex AI (Gemini) (AI Model Layer), Memorystore/Vector (Knowledge & Memory Layer), Apigee / MCP Server (Tool & Integration Layer).
1. Retrieve active user session & relevant memory context
2. Return historical facts, entities & conversational state (response)
3. Prompt LLM for task decomposition & tool call selection
4. Output structured tool arguments & planned step (response)
5. Validate action impact against HITL safety policy
6. Forward approved invocation via Model Context Protocol
7. Return tool payload execution result & telemetry (response)

### Layer: Tool & Integration
*Purpose:* Connect agents to enterprise tools, APIs and other agents using standard protocols and registries.

| Category | Component | Sub-label |
|---|---|---|
| Coding Plane | MCP Server (Gemini Enterprise) | MCP |
| Coding Plane | A2A (Cloud Run + Apigee) | A2A Protocol |
| Core | MCP (Model Context Protocol) | Core protocol |
| Core | A2A Protocol | Core protocol |
| Integration | Integration Connectors (MCP) | Tool Connectors |
| Integration | Apigee | API Gateway |
| Integration | Apigee API Hub | Tool Registry |
| Integration | Code Execution Gemini | Code Execution Sandbox |

**Interaction sequence — model-tool connection, sandboxing & protocol flow** (tool discovery in registries, secure execution sandboxing, A2A cross-agent comms). Participants: Vertex Agent Bldr, Apigee API Hub (Tool Registry), Apigee / MCP Server (Gateway), Code Execution Gemini (Sandbox), Data & Systems (Enterprise Systems & APIs).
1. Query tool schema & endpoint metadata definition
2. Return OpenAPI / MCP schema and credentials scope (response)
3. Execute standardized MCP tool call request
4. Spin up isolated sandbox for unsafe code execution
5. Query enterprise API / system of record endpoint
6. Return structured dataset & telemetry response
7. Send formatted observations back to orchestrator

### Layer: Knowledge & Memory
*Purpose:* Maintain context and ground agent reasoning in enterprise knowledge using session, long-term and vector-based stores.

| Category | Component | Sub-label |
|---|---|---|
| Core | Context Engineering | Core capability |
| Memory | Memorystore (Redis) | Short-term Session Memory |
| Memory | Firestore | Long-term Knowledge Memory |
| Memory | Memory Bank | Long-term store |
| Memory | Vertex AI Search/Vector Search | RAG Pipeline |

**Interaction sequence — context engineering, hybrid search & memory lifecycle flow** (real-time session caching, semantic vector search grounding, episodic knowledge recall). Participants: Vertex Agent Bldr, Memorystore Redis (Session), Vertex Vector Search (Vector), Firestore / Memory (Long-term), GCS / BigQuery (Enterprise Data Layer).
1. Read active conversation window & working memory
2. Perform hybrid dense/sparse vector similarity query
3. Fetch document chunks & ground truth embeddings
4. Return top-k relevant knowledge passages (response)
5. Inject ranked context citations into agent reasoning prompt
6. Persist key decisions, facts & summarized knowledge
7. Confirm long-term episodic memory index update (response)

### Layer: AI Model
*Purpose:* Supply the underlying intelligence and govern safe model access including code generation, generative AI and classical ML models.

| Category | Component | Sub-label |
|---|---|---|
| Coding Plane | Vertex AI (Gemini) | Code Generation |
| Coding Plane | Gemini Code Assist | Gen AI Models |
| Model | Vertex AI AutoML | Classical ML |
| Model | Model Garden | Foundation Models |
| Model | Vertex AI Training Job | Model Training |
| Model | BQML | ML on BigQuery |
| Integration | Cloud Gateway | Foundation Model Gateway |
| Integration | Vertex AI Safety Filters | Guardrails |

**Interaction sequence — model routing, guardrails enforcement & inference flow** (intelligent model routing, safety guardrail screening, fallback routing, LLM inference). Participants: Vertex Agent Bldr, Cloud Model Gateway (AI Model – Gateway), Vertex Safety Filter (AI Model – Guardrails), Vertex AI Gemini (AI Model – LLM), Model Monitoring (Security & Governance).
1. Dispatch generation request with temperature & tools
2. Pre-screen input prompt for jailbreaks, PII & toxic content
3. Route sanitized prompt to optimal foundation model
4. Stream raw model tokens back through output filters
5. Validate response alignment & hallucination thresholds
6. Deliver verified response & usage tokens to agent
7. Stream audit telemetry & cost metrics to monitoring

---

## 4. DATA group

### Layer: Enterprise Data & Systems
*Purpose:* Provide the data and systems of record that agents read from and act on — structured, unstructured, graph and warehouse data.

| Category | Component | Sub-label |
|---|---|---|
| Structured | Cloud SQL / AlloyDB | RDBMS |
| Unstructured | Firestore | NoSQL |
| Graph | Cloud Spanner | Relational / Graph |
| Unstructured | Vertex AI Vector Search | Vector Database |
| Graph | EKG | Knowledge Graph |
| Applications | SAP / Salesforce on GCP | ERP/CRM |
| Applications | Enterprise Connectors | ITSM / Integration |
| Warehouse | GCS + BigQuery | Data Lake / Warehouse |

**Interaction sequence — enterprise data ingestion, retrieval & consistency flow** (structured DB transactions, vector indexing, enterprise connector queries). Participants: Enterprise Connect. (Tool & Integration Layer), Cloud SQL / AlloyDB (SQL), Spanner / EKG (Graph), Vertex Vector Search (Vector), Private Service Connect (Infra / Security Layer).
1. Execute ACID transaction / relational entity query
2. Return structured table records & status code (response)
3. Query entity relationships across knowledge graph
4. Return multi-hop graph nodes and attributes (response)
5. Upsert newly generated embeddings & metadata tags
6. Replicate data securely over private network channels
7. Confirm encrypted persistent storage write (response)

---

## 5. INFRASTRUCTURE group

### Layer: Deployment Layer
*Purpose:* Host and run the platform across cloud and on-premise environments with Kubernetes, serverless and hybrid deployment options.

| Category | Component | Sub-label |
|---|---|---|
| Kubernetes | Google Kubernetes Engine | Container orchestration |
| PaaS | Cloud Run | Managed container hosting |
| Serverless | Cloud Functions | Serverless compute |
| Multi-cloud | Distributed Cloud | Hybrid / Multi-cloud |
| On-premise | Cloud Run for Anthos | On-premise GCP |

**Interaction sequence — container hosting, serverless compute & scalability flow.** Participants: Agent Workloads (Multi-Agent Solution), Google Kubernetes (GKE) (K8s), Cloud Run / Functions (Serverless), Distributed Cloud/Anthos (Hybrid), Security Command Ctr (Security & Governance).
1. Trigger event-driven agent tool execution instance
2. Autoscaling request to Kubernetes node pool for inference
3. Synchronize workload state across hybrid/on-prem clusters
4. Rebalance compute capacity dynamically (response)
5. Allocate high-throughput GPU/CPU compute runtime
6. Stream runtime CPU, latency & container metrics (to Security Command Center)

---

## 6. Cross-cutting: Security & Governance (purple columns)

Shown on the L3 overview as two columns — **Security** and **Governance** (each with "View layer detail →"). Each column is split into groups, tagged with the layers it covers.

### Security
| Group (layers covered) | Components |
|---|---|
| IDENTITY & DELEGATION (Engagement & Multi-Agent) | Cloud Identity + Workload Identity Federation |
| ADVERSARIAL AI & MODEL DEFENSE (Agentic & AI Model) | Vertex AI Safety Filter & Model Armor; Vertex AI Agent Policy Gating |
| TOOL & RUNTIME SANDBOXING (Tool & Integration) | gVisor / Cloud Run Isolated Sandbox |
| DATA, SECRETS & PRIVACY (Knowledge & Enterprise Data) | Cloud KMS + Secret Manager; Cloud Sensitive Data Protection (DLP); Vertex Search Access Controls & GCS ACLs |
| PERIMETER & THREAT POSTURE (Deployment Infra) | Private Service Connect & VPC-SC; Artifact Analysis (SBOM & Binary Authorization); SCC (Security Command Center) |

### Governance
| Group (layers covered) | Components |
|---|---|
| ACCESS & MODEL REGISTRY (Users & AI Model) | Cloud IAM; Apigee / API Hub (Agent Registry); Vertex AI Model Registry; Cloud IAM (RBAC/ABAC) |
| RESPONSIBLE AI & QUALITY (Multi-Agent AI & Knowledge) | Vertex AI Model Cards; Fairness Indicators; Vertex AI Model Monitoring; Vertex AI Safety Filters; Dataplex AI Governance & Risk Assessment |
| FINOPS & DATA LIFECYCLE (Data & Infra) | Cloud Billing / Recommender; Data Catalog / Lifecycle; Backup and DR Service |

> Note: the per-group assignment of a few governance items was read from a partly overlapped screenshot, so treat the grouping as approximate. The flat list on the Security & Governance drill-down page is authoritative.

### Security & Governance drill-down page (flat lists)
**Security Components (10):** Cloud Identity + Workload Identity Federation · Vertex AI Safety Filter & Model Armor · Vertex AI Agent Policy Gating · gVisor / Cloud Run Isolated Sandbox · Cloud KMS + Secret Manager · Cloud Sensitive Data Protection (DLP) · Vertex Search Access Controls & GCS ACLs · Private Service Connect & VPC-SC · Artifact Analysis (SBOM & Binary Authorization) · SCC (Security Command Center)

**Governance Components (12):** Cloud IAM · Apigee / API Hub (Agent Registry) · Vertex AI Model Registry · Vertex AI Model Cards · Fairness Indicators · Vertex AI Model Monitoring · Vertex AI Safety Filters · Dataplex AI Governance & Risk Assessment · Cloud Billing / Recommender · Cloud IAM (RBAC/ABAC) · Data Catalog / Lifecycle · Backup and DR Service

**Interaction sequence — cross-cutting security, policy guardrails & governance flow** (end-to-end policy enforcement, IAM authentication, drift detection, compliance auditing). Participants: All Platform Layers (Users / Channels / Agents), Cloud IAM & KMS (Sec & Gov Component – IAM), Vertex Safety & DLP (Sec & Gov Component – Safety), Model Cards / SCC (Sec & Gov Component – Audit), Data & Model Assets (Enterprise Assets).
1. Validate request token signature & permission scope
2. Enforce zero-trust attribute & rate-limit policies
3. Verify encryption-at-rest keys & PII redaction masks
4. Log immutable transaction traces & model inferences
5. Evaluate bias, drift, fairness & cost thresholds (self-call)
6. Issue compliance attestations & authorize execution (response)

---

## 7. Quick index: layer → GCP services
| Layer | GCP services |
|---|---|
| User | Firebase Auth (Identity Platform), Cloud Identity, Workforce IDP, IAP, IAM |
| Channels | Firebase Hosting, Firebase Cloud Messaging, Cloud Run, Dialogflow CX, CCAI, Speech-to-Text/TTS, Vertex AI Agent Builder |
| Business Process | Cloud Workflows, Composer, Looker, Document AI, Workday on GCP, App Integration |
| Agentic Orchestration | Gemini Code Assist, Agent Studio, Vertex AI Agent Builder, Vertex AI (Gemini), Gen AI Eval Service, Agent Tools/Extensions, Workflows + Firestore + Pub/Sub |
| Tool & Integration | MCP Server (Gemini Enterprise), A2A (Cloud Run + Apigee), Integration Connectors, Apigee, Apigee API Hub, Code Execution Gemini |
| Knowledge & Memory | Memorystore (Redis), Firestore, Memory Bank, Vertex AI Search/Vector Search |
| AI Model | Vertex AI (Gemini), Gemini Code Assist, Vertex AI AutoML, Model Garden, Vertex AI Training Job, BQML, Cloud Gateway, Vertex AI Safety Filters |
| Enterprise Data & Systems | Cloud SQL/AlloyDB, Firestore, Cloud Spanner, Vertex AI Vector Search, EKG, SAP/Salesforce on GCP, Enterprise Connectors, GCS + BigQuery |
| Deployment | GKE, Cloud Run, Cloud Functions, Distributed Cloud, Cloud Run for Anthos |
| Security & Governance | see section 6 |
