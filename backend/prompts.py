"""Knowledge-base loading and the strict prompt."""
import json
from pathlib import Path

from catalog import CATALOG, LAYERS, canonical_service, usage_unit  # noqa: F401  (canonical_service re-exported)
from schemas import ENVS

KB_DIR = Path(__file__).resolve().parent.parent / "KnowledgeBase"


def _section(text: str, start: str, end: str | None = None) -> str:
    i = text.find(start)
    if i < 0:
        return ""
    j = text.find(end, i + len(start)) if end else -1
    return text[i : j if j > 0 else len(text)].strip()


def load_kb() -> str:
    """Pull the parts of the three KB files the agent needs as reference context."""
    parts = []
    f1 = KB_DIR / "01_Architecture_Overview.md"
    f2 = KB_DIR / "02_L3_GCP_Component_Overview.md"
    f3 = KB_DIR / "03_GCP_BOM.md"
    if f1.exists():
        t = f1.read_text(encoding="utf-8")
        parts.append("### Architecture layers (L2)\n" + _section(t, "## 2. Layer stack", "### Diagram"))
    if f2.exists():
        t = f2.read_text(encoding="utf-8")
        parts.append("### L3 GCP layer -> services index\n" + _section(t, "## 7. Quick index"))
        parts.append("### Security & Governance components (L3 GCP)\n" + _section(t, "## 6. Cross-cutting", "## 7. Quick index"))
    if f3.exists():
        t = f3.read_text(encoding="utf-8")
        parts.append("### GCP Bill of Materials\n" + _section(t, "## 1. Recommended", "## 3. Notes"))
    return "\n\n".join(p for p in parts if p.strip())


SCHEMA_EXAMPLE = {
    "assumptions": ["short sizing assumption"],
    "exclusions": ["Network egress to the internet", "Google Cloud support plan"],
    "mcp_tools": ["order_lookup", "customer_search"],
    "layer_purposes": {
        "data": "Keeps the order and customer records the support agent must read to answer status questions",
        "model": "Supplies the reasoning and answer writing for customer order questions",
        "sec_perimeter": "Shields the public chat channel from web attacks"},
    "components": [
        {"group": "fixed", "layer": "data", "service": "Cloud SQL", "logical": "RDBMS",
         "purpose": "Stores order status and shipment history that the agent looks up per customer",
         "reason": "Holds the order records the agent queries", "qty_reason": "1 HA instance per env; PROD needs failover",
         "sku_tier": "PostgreSQL, HA", "vcpu": 4, "ram_gb": 16, "qty": {e: 1 for e in ENVS}},
        {"group": "fixed", "layer": "model", "service": "Vertex AI Gemini (LLM)", "logical": "Generative AI Model",
         "purpose": "Understands the customer's question and writes the order-status reply",
         "reason": "Reasons over questions and writes the answers", "qty_reason": "1 endpoint per env; volume sized from daily users",
         "sku_tier": "Gemini 2.5 Flash",
         "vcpu": 0, "ram_gb": 0, "qty": {e: 1 for e in ENVS}, "usage": {"DEV": 5, "SIT": 5, "UAT": 10, "PROD": 140}},
        {"group": "fixed", "layer": "model", "service": "Vertex AI Gemini Output (LLM)", "logical": "Generative AI Model",
         "purpose": "Pays for the reply text the model writes back to the customer",
         "reason": "Output tokens are billed separately from input tokens", "qty_reason": "same endpoint as the input row",
         "sku_tier": "Gemini 2.5 Flash",
         "vcpu": 0, "ram_gb": 0, "qty": {e: 1 for e in ENVS}, "usage": {"DEV": 2, "SIT": 2, "UAT": 4, "PROD": 60}},
        {"group": "fixed", "layer": "process", "service": "Document AI", "logical": "Document Processing",
         "purpose": "Reads the policy PDFs the agent answers from",
         "reason": "OCR of the policy documents", "qty_reason": "1 processor in PROD only",
         "sku_tier": "OCR", "vcpu": 0, "ram_gb": 0, "qty": {"DEV": 0, "SIT": 0, "UAT": 0, "PROD": 1},
         "usage": {"DEV": 0, "SIT": 0, "UAT": 0, "PROD": 8}, "build_usage": 25},
        {"group": "nfr", "layer": "sec_perimeter", "service": "Cloud Armor", "logical": "Perimeter Security",
         "purpose": "Filters malicious traffic before it reaches the public chat channel",
         "reason": "WAF in front of the public chat channel", "qty_reason": "1 policy per env",
         "sku_tier": "WAF policy", "vcpu": 0, "ram_gb": 0, "qty": {e: 1 for e in ENVS}},
    ],
}


def _allowed_block() -> str:
    lines = {"fixed": [], "nfr": []}
    for name, s in CATALOG.items():
        u = usage_unit(name)
        lines[s["group"]].append(f"- {name} (count unit: {s['unit']}" + (f"; usage unit: {u})" if u else ")"))
    return ("FIXED / PLATFORM services (group \"fixed\"):\n" + "\n".join(lines["fixed"])
            + "\n\nNON-FUNCTIONAL services (group \"nfr\"):\n" + "\n".join(lines["nfr"]))


def _layers_block() -> str:
    out = []
    for kind, title in (("fr", "FUNCTIONAL (FR) layers - use with group \"fixed\""),
                        ("nfr", "NON-FUNCTIONAL (NFR) layers: Security, Governance, Operations - use with group \"nfr\"")):
        out.append(title + ":")
        for l in LAYERS:
            if l["kind"] == kind:
                out.append(f"- {l['id']} = {l['name']} [{l['section']}]: {l['purpose']}. Typical GCP services: {l['ref']}")
        out.append("")
    return "\n".join(out).strip()


def build_prompt(use_case: str, nfr: str, region: str, kb: str, previous_error: str | None = None):
    """Return (system, user) prompt strings."""
    system = f"""You are a senior Google Cloud solution architect producing an enterprise-grade bill of materials for an agentic AI application.
Use the reference architecture below to decide which layers and GCP services the solution needs.

# Reference architecture (knowledge base)
{kb}

# Architecture layers (set each component's "layer" to one of these ids)
{_layers_block()}

# Allowed services (use these names exactly)
{_allowed_block()}

# Rules
1. Build the solution ENTIRELY on Google Cloud. Choose ONLY services from the allowed list above (every one is a GCP product that has a GCP price), spelled exactly as written, and map each knowledge-base component to the GCP service named in the knowledge base. Never add third-party, other-cloud or on-premises products; where no allowed service fits, leave it out rather than invent one.
2. Be thorough and enterprise-level: include EVERY service the solution genuinely needs across all layers - channels and identity, agent platform / orchestration runtime, the LLM (model name in sku_tier), MCP servers and tool/API gateway, memory and knowledge stores, enterprise data, deployment and networking, CI/CD and registry, and eventing. Do not stop at the obvious ones.
3. Group "fixed" = the functional (FR) solution: components that deliver the use case, each placed in one of the FR layers. Group "nfr" = non-functional components that satisfy the NFRs, each placed in one of the NFR layers (security, governance, operations). Cover EVERY FR layer the use case touches and EVERY NFR layer, mapping each NFR component to the layer it protects or governs. Include a sensible enterprise baseline of "nfr" components even when the NFR text is short, and scale them to the stated NFRs (availability, latency, throughput, peak, RTO/RPO, compliance, data residency, retention).
4. Environments are exactly: {', '.join(ENVS)}. Give an integer count for each environment (0 if the component is not needed there). Non-production is normally smaller than PROD, and PROD has redundancy where the NFRs call for it.
5. "layer" must be exactly one layer id from the list above (an FR layer for group "fixed", an NFR layer for group "nfr"). "qty" is the NUMBER OF COMPONENTS of that service (instances / nodes / clusters / replicas / resources, in the count unit shown) per environment. Also give four short text fields for every component: "purpose" = one sentence on what this component does for THIS use case, in the use case's own terms (never a generic description of the GCP product); "logical" = the logical component from the knowledge base's Logical -> Physical Component Mapping that this service realises (e.g. "Generative AI Model", "Short-Term Session Memory"; a short logical name if none fits); "reason" = one sentence on why this service is needed for THIS use case; "qty_reason" = one sentence on why this number of instances per environment.
6. For compute and database services (Compute Engine VM, Cloud Run, MCP Server, Cloud SQL, AlloyDB) set "vcpu" and "ram_gb" for ONE instance. For everything else use 0.
7. sku_tier is a short concrete size / edition / model (e.g. "e2-standard-4", "PostgreSQL, HA", "Gemini 2.5 Flash", "Standard tier"). ONE sku_tier per row, applied to all environments. If environments need different sizes, use separate rows (the environments that do not use that size get 0).
8. Use region "{region}" unless the use case clearly needs another GCP region.
9. "mcp_tools" lists the MCP tools / tool endpoints this solution needs (short snake_case names, e.g. "order_lookup"). Put MCP server hosting in components using the "MCP Server (Cloud Run)" service.
10. For every service that shows a "usage unit" above, also set "usage": the estimated TOTAL monthly volume per environment, as a number of that usage unit (e.g. usage unit "1M input tokens" and 200 means 200 million tokens a month). Derive it from the users, traffic, peak and retention in the use case and NFRs; non-production is much smaller than PROD. Omit "usage" for all other services.
11. "layer_purposes" maps EVERY layer id you used in components to one sentence on what that layer does for THIS use case (name the real data, users, channels or risks of the use case; never a generic definition of the layer). "assumptions" lists the key sizing and design assumptions you made (short sentences), including the basis of each usage estimate (e.g. 1 lakh chats/day x 4K tokens = 12,000M tokens/month).
12. Keep every text value short and plain: never use double quotes, backslashes or line breaks inside a value. The JSON must be valid and complete.
13. GCP costing method (how a real GCP estimate is built; follow it):
 a) Fixed capacity (clusters, instances, gateways, search nodes) is counted per environment in "qty"; consumption (tokens, calls, queries, pages, messages, log GB, storage GB) goes in "usage" per environment. Always-on items are billed for 730 hours a month.
 b) LLM tokens: use TWO rows with the same model in sku_tier - "Vertex AI Gemini (LLM)" for INPUT tokens and "Vertex AI Gemini Output (LLM)" for OUTPUT tokens. Estimate chats x turns x tokens per turn, with input (prompt + retrieved context + history) usually 2-3x the output. If the solution retrieves documents, add "Vertex AI Embeddings" (tokens embedded for the initial load plus monthly updates and one query per search).
 c) Use the cheapest model that meets the quality need (a Flash model for routine lookups and answers; Pro only for hard reasoning). DEV and SIT use a small volume; UAT is a load-test sample; PROD carries the real traffic.
 d) Databases: size vCPU / RAM per environment (smaller in non-production, "HA" only where the NFRs need it) and ALSO add a "Cloud SQL Storage" row (or "AlloyDB Storage" for AlloyDB; usage = GB stored, same sku_tier as the database) because disk is billed apart from compute.
 e) APIs and integration: "API Gateway" (usage = millions of calls) for light traffic to order / CRM / tool APIs; use "Apigee" only for an enterprise API programme. "Application Integration" (usage = thousands of executions) for workflow connections to enterprise systems. Eventing: "Pub/Sub" (usage = TiB). Search over documents: "Vertex AI Search" (usage = thousands of queries) or "Vertex AI Vector Search".
 f) One-time build volume: when a service has a one-off initial load that is not repeated monthly (initial document OCR / ingestion, embedding the knowledge base, first bulk log load), put that volume in "build_usage" (same usage unit; 0 if none). Keep it OUT of the monthly "usage".
 h) sku_tier picks the price for these services, so write it exactly: "Model Garden" rows - the model name (e.g. "Llama 4 Scout", "Deepseek V3.2"), one row for input and one for output tokens; "Vertex AI AutoML" - data type + stage (e.g. "Image Classification Model Training", "Structured Data Model Deployment"), usage = node-hours; "Vertex AI Training Job" - machine family "N1 Predefined", usage = vCPU-hours, plus a "Vertex AI Training Job RAM" row (usage = GiB-hours); "Looker" - "Standard Edition", "Standard User", "Developer User" or "Viewer User" (qty = editions or users); "Google Distributed Cloud" - "Bare Metal" or "vSphere" (qty = vCPUs); "Gemini Code Assist" - qty = licensed users; "Gen AI Evaluation Service" - input and output token rows; "BigQuery ML" - usage = TiB processed (use "BigQuery ML Training" for model creation); "Code Execution Sandbox" - usage = vCPU-hours.
 g) Security Command Center is an organisation-wide subscription with a $15,000-a-year minimum: give it ONE instance, in PROD only (0 in DEV, SIT, UAT). "exclusions" lists what this estimate deliberately leaves out (e.g. internet egress, Google Cloud support plan, committed-use discounts, third-party licences, people and build effort, taxes). Keep each to a few words.
14. Respond with ONE JSON object and nothing else (no markdown, no prose). Shape:
{json.dumps(SCHEMA_EXAMPLE, indent=2)}"""
    user = f"Use case / functional requirement:\n{use_case.strip()}"
    user += f"\n\nNon-functional requirements:\n{nfr.strip() or '(none given - assume a standard enterprise baseline)'}"
    if previous_error:
        user += f"\n\nYour previous answer was rejected: {previous_error}\nReturn corrected JSON only."
    return system, user
