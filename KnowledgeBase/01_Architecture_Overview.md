# Architecture Overview (L2) — IBM Multi-Agent Systems Reference Architecture

> Source: IBM · Multi-Agent Systems Reference Architecture (Beta v0.9, 30 October 2026, "Made with IBM Bob").
> Section path: `04 Architecture → B. L2 Architecture Overview` (breadcrumb: L1: System Context › L2: Overview).
> Purpose of this file: knowledge-base reference for the layered logical architecture of Agentic AI systems. The cloud-specific mapping is in `02_L3_GCP_Component_Overview.md` and the GCP bill of materials is in `03_GCP_BOM.md`.

## 1. Page description
**L2 : Architecture Overview** — "High-level enterprise architecture of Agentic AI systems — click any layer block to explore its components."

UI hints on the page:
- Click a **layer block** to drill into that layer.
- Click a **group label** (e.g. ENGAGEMENT) to see all layers in that group.
- Use the **Component Overview** tab for a full table view.
- Button: **"View Full Component Overview Table →"** (leads to L3 Component Overview).
- Button: **"← Back to L1: System Context"**.

## 2. Layer stack (top → bottom)

| Group (vertical label) | Layer block | Notes |
|---|---|---|
| **USERS** | User | Human and system consumers |
| **ENGAGEMENT** | Channels | Channels through which users interact |
| **ENGAGEMENT** | Business Process – Workflows & Applications | Business processes, workflows, app integrations |
| **MULTI AGENT SOLUTION** (dashed boundary around 4 layers) | Agentic Orchestration | Plan, reason, orchestrate agents |
| **MULTI AGENT SOLUTION** | Tool & Integration | Tools, APIs, other agents |
| **MULTI AGENT SOLUTION** | Knowledge & Memory | Session / long-term / vector knowledge |
| **MULTI AGENT SOLUTION** | AI Model | LLMs, ML models, guardrails |
| **DATA** | Enterprise Data & Systems | Systems of record |
| **INFRA** | Deployment Layer | Hosting / runtime |
| *(cross-cutting, right side, full height — purple block)* | **Security & Governance** | Spans every layer above |

### Diagram (text form)
```
+-------------------------------------------------------------+  +-----------+
| USERS        | User                                         |  |           |
+-------------------------------------------------------------+  |           |
| ENGAGEMENT   | Channels                                     |  |           |
|              | Business Process – Workflows & Applications  |  |           |
+- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+  | Security  |
| MULTI AGENT  | Agentic Orchestration                        |  |    &      |
| SOLUTION     | Tool & Integration                           |  | Governance|
|              | Knowledge & Memory                           |  |           |
|              | AI Model                                     |  |           |
+- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -+  |           |
| DATA         | Enterprise Data & Systems                    |  |           |
+-------------------------------------------------------------+  |           |
| INFRA        | Deployment Layer                             |  |           |
+-------------------------------------------------------------+  +-----------+
```

## 3. Layer purposes (as stated on the L3 pages)

| Layer | Purpose statement |
|---|---|
| User | Represent all human and system consumers interacting with the (Agentic AI) platform. |
| Channels | Provide the digital and conversational channels through which users interact with the platform. |
| Business Process – Workflows & Applications | Orchestrate business processes, workflows, and enterprise application integrations. |
| Agentic Orchestration | Plan, reason and orchestrate autonomous agent behavior including task decomposition, skill management and human-in-the-loop (HITL) checkpoints. |
| Tool & Integration | Connect agents to enterprise tools, APIs and other agents using standard protocols and registries. |
| Knowledge & Memory | Maintain context and ground agent reasoning in enterprise knowledge using session, long-term and vector-based stores. |
| AI Model | Supply the underlying intelligence and govern safe model access including code generation, generative AI and classical ML models. |
| Enterprise Data & Systems | Provide the data and systems of record that agents read from and act on — structured, unstructured, graph and warehouse data. |
| Deployment Layer | Host and run the platform across cloud and on-premise environments with Kubernetes, serverless and hybrid deployment options. |
| Security & Governance | Cross-cutting security and governance concerns (identity, adversarial defense, sandboxing, data privacy, perimeter, access/model registry, responsible AI, FinOps). |

## 4. Cloud platform views
Every L3 page offers a **Cloud Platform** selector with six views:
`Generic (Logical)` · `Azure` · `GCP` · `AWS` · `IBM` · `IBM Enterprise Advantage`

L3 sub-pages under section 04 Architecture:
- A. L1 System Context Diagram
- B. L2 Architecture Overview
- C. L3 Component Overview
- D. L3 — Azure Implementation
- E. L3 — AWS Implementation
- F. L3 — GCP Implementation
- G. L3 — IBM Technology Implementation
- H. L3 — IBM Enterprise Advantage Architecture

## 5. Site navigation (table of contents of the reference architecture)

| # | Section | Sub-title / contents |
|---|---|---|
| 01 | Foundations | Business context & key concepts |
| 02 | Requirements | Functional vs. non-functional |
| 03 | Architecture Principles, Patterns & Key Decisions | Design principles, patterns, topologies & ADRs — subsections: A. Multi-Agent System Design Principles, B. Architecture Patterns, C. Agentic AI Decision Map |
| 04 | Architecture | Layered design & multi-cloud mapping (A–H above) |
| 05 | Path to Production | Adoption roadmap & risk mitigation |
| 06 | Operations | AgentOps & observability |
| 08 | Security & Privacy | Threat model & controls |
| 09 | BOM & Volumetrics | Bill of materials, BOQ & cost modelling — A. BOM (Azure / AWS / GCP / IBM), B. BOQ |

(There is no section 07 in the navigation.)

## 6. Standard per-layer page structure (L3 drill-down)
Each layer drill-down page has the same structure:
1. Header band: group label (e.g. ENGAGEMENT), layer name with cloud badge (e.g. `GCP`), purpose sentence.
2. Cloud Platform selector.
3. **Physical Components Breakdown** — cards with category tag, component name, sub-label, and an "i" tooltip.
4. Optional **Coding Plane** band — "core engineering components for building & maintaining agents".
5. **Purpose & Inter-Layer Interaction Sequence** — a sequence diagram ("Selected Layer Components" highlighted dark; "Connected External Layers" light; solid arrow = Request, dashed arrow = Response / Stream).

## 7. Key takeaways for downstream use
- The architecture has **9 layer blocks** in 6 groups (User, Channels, Business Process, Agentic Orchestration, Tool & Integration, Knowledge & Memory, AI Model, Enterprise Data & Systems, Deployment) plus one cross-cutting **Security & Governance** column.
- The four **Multi Agent Solution** layers (Orchestration, Tool & Integration, Knowledge & Memory, AI Model) are the core "agentic" platform.
- Logical components are provider-neutral; each is mapped to physical services per cloud (see the GCP files for the GCP mapping).
