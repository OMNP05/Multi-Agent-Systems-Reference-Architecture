"""GCP service catalog: the services the LLM may choose from and how each one is priced.

group : "fixed" -> fixed infrastructure & platform services table
        "nfr"   -> non-functional components table (security, resilience, observability)
mode  : "hour"  qty x hours x price per unit-hour
        "shape" qty (instances) x hours x (vCPU x cpu_hr + RAM GiB x ram_hr)
        "month" qty x flat monthly price
        "usage" priced per usage unit (volume unknown, so no monthly total)
catalog : Cloud Billing Catalog display-name candidates (first match wins)
req/pref: description tokens a SKU must contain (req) / is ranked higher for (pref)
static  : approximate list price (USD) used only when the live catalog gives no match
"""

CATALOG: dict = {}


def _add(name, group, unit, mode, static, catalog, req=(), pref=(), plabel=None, aliases=(), **extra):
    CATALOG[name] = dict(group=group, unit=unit, mode=mode, static=static, catalog=list(catalog),
                         req=list(req), pref=list(pref), plabel=plabel, aliases=list(aliases), **extra)


# ---------------------------------------------------------------- fixed / platform
_add("Google Kubernetes Engine (cluster)", "fixed", "cluster", "hour", 0.10, ["Kubernetes Engine"],
     pref=["cluster", "management", "fee"], aliases=["gke", "google kubernetes engine", "gke cluster"])
_add("Compute Engine VM", "fixed", "VM", "shape", None, ["Compute Engine"], shape="compute",
     static_cpu=0.0335, static_ram=0.0045, aliases=["compute engine", "gce", "gke node pool", "gke nodes"])
_add("Cloud Run (min instances)", "fixed", "instance", "shape", None, ["Cloud Run"], shape="cloudrun",
     static_cpu=0.009, static_ram=0.001, aliases=["cloud run", "cloud run service"])
_add("MCP Server (Cloud Run)", "fixed", "instance", "shape", None, ["Cloud Run"], shape="cloudrun",
     static_cpu=0.009, static_ram=0.001, aliases=["mcp server", "mcp servers", "custom mcp server"])
_add("Cloud Functions", "fixed", "function", "usage", 0.40, ["Cloud Functions"], pref=["invocations"],
     plabel="per 1M invocations", aliases=["cloud functions (2nd gen)"])
_add("Cloud SQL", "fixed", "instance", "shape", None, ["Cloud SQL"], shape="cloudsql",
     static_cpu=0.0413, static_ram=0.007, aliases=["cloud sql for postgresql", "cloud sql postgresql", "postgresql"])
_add("AlloyDB", "fixed", "instance", "shape", None, ["AlloyDB for PostgreSQL", "AlloyDB"], shape="alloydb",
     static_cpu=0.0661, static_ram=0.0112, aliases=["alloydb for postgresql"])
_add("Cloud Spanner", "fixed", "node", "hour", 0.90, ["Cloud Spanner"], pref=["node", "regional"],
     aliases=["spanner"])
_add("Firestore", "fixed", "database", "usage", 0.06, ["Cloud Firestore", "Firestore"], pref=["read", "entity", "document"],
     plabel="per 100K reads")
_add("Memorystore for Redis", "fixed", "GB", "hour", 0.05, ["Cloud Memorystore for Redis", "Memorystore for Redis"],
     pref=["standard", "basic", "capacity"], aliases=["memorystore", "redis"])
_add("Vertex AI Vector Search", "fixed", "node", "hour", 0.75, ["Vertex AI"],
     pref=["vector", "search", "index", "serving"], aliases=["vector search", "matching engine"])
_add("Vertex AI Agent Engine", "fixed", "agent runtime", "usage", 0.0864, ["Vertex AI"],
     pref=["agent", "engine", "runtime"], plabel="per vCPU-hour", aliases=["agent engine", "vertex ai agent builder", "agent builder"])
_add("Vertex AI Gemini (LLM)", "fixed", "model endpoint", "usage", 1.25, ["Vertex AI", "Generative Language API"],
     pref=["gemini", "input", "token"], plabel="per 1M input tokens", aliases=["gemini", "vertex ai gemini", "gemini api"])
_add("Vertex AI Search", "fixed", "app", "usage", 4.00, ["Discovery Engine", "Vertex AI Search"],
     pref=["search", "queries", "query"], plabel="per 1K queries", aliases=["vertex ai search and conversation", "discovery engine"])
_add("Vertex AI Prediction Endpoint", "fixed", "node", "hour", 0.60, ["Vertex AI"],
     pref=["prediction", "online", "node"], aliases=["vertex ai endpoint", "model endpoint"])
_add("Dialogflow CX", "fixed", "agent", "usage", 7.00, ["Dialogflow"], pref=["cx", "text", "request"],
     plabel="per 1K requests", aliases=["dialogflow"])
_add("Document AI", "fixed", "processor", "usage", 1.50, ["Document AI", "Cloud Document AI"], pref=["page", "ocr"],
     plabel="per 1K pages")
_add("Speech-to-Text", "fixed", "service", "usage", 0.024, ["Cloud Speech-to-Text", "Speech-to-Text"], pref=["standard", "audio"],
     plabel="per minute of audio", aliases=["speech to text", "stt"])
_add("Text-to-Speech", "fixed", "service", "usage", 16.00, ["Cloud Text-to-Speech", "Text-to-Speech"], pref=["character", "standard", "wavenet"],
     plabel="per 1M characters", aliases=["text to speech", "tts"])
_add("Apigee", "fixed", "environment", "hour", 0.50, ["Apigee"], pref=["environment", "pay", "go"],
     aliases=["apigee x", "apigee api hub", "api gateway"])
_add("Cloud Composer", "fixed", "environment", "hour", 0.35, ["Cloud Composer"], pref=["small", "environment", "composer"],
     aliases=["composer"])
_add("Cloud Workflows", "fixed", "workflow", "usage", 0.01, ["Workflows", "Cloud Workflows"], pref=["step", "internal", "external"],
     plabel="per 1K steps", aliases=["workflows"])
_add("Pub/Sub", "fixed", "topic", "usage", 40.00, ["Cloud Pub/Sub", "Pub/Sub"], pref=["message", "delivery", "throughput"],
     plabel="per TiB", aliases=["pubsub", "cloud pub/sub", "cloud pubsub"])
_add("Cloud Scheduler", "fixed", "job", "month", 0.10, ["Cloud Scheduler"], pref=["job"])
_add("Cloud Storage", "fixed", "bucket", "usage", 0.023, ["Cloud Storage"], pref=["standard", "storage"],
     plabel="per GB-month", aliases=["gcs", "cloud storage bucket"])
_add("BigQuery", "fixed", "dataset", "usage", 6.25, ["BigQuery"], pref=["analysis", "query", "queries"],
     plabel="per TiB scanned", aliases=["bigquery dataset"])
_add("Artifact Registry", "fixed", "repository", "usage", 0.10, ["Artifact Registry"], pref=["storage"],
     plabel="per GB-month")
_add("Cloud Build", "fixed", "pipeline", "usage", 0.003, ["Cloud Build"], pref=["build", "minute"],
     plabel="per build-minute", aliases=["cloud build pipeline"])
_add("Cloud Load Balancing", "fixed", "forwarding rule", "hour", 0.025, ["Networking"],
     req=["forwarding", "rule"], pref=["load", "balancing", "application"], aliases=["load balancer", "external application load balancer", "https load balancer"])
_add("Cloud DNS", "fixed", "managed zone", "month", 0.20, ["Cloud DNS"], pref=["zone", "managed"])
_add("Identity Platform", "fixed", "tenant", "usage", 0.0055, ["Identity Platform", "Identity Toolkit"], pref=["monthly", "active", "users"],
     plabel="per MAU", aliases=["firebase auth", "firebase authentication"])

# ---------------------------------------------------------------- non-functional
_add("Cloud Armor", "nfr", "security policy", "month", 5.00, ["Cloud Armor", "Networking"],
     req=["armor"], pref=["policy", "security"], aliases=["cloud armor waf", "waf"])
_add("Cloud CDN", "nfr", "origin", "usage", 0.08, ["Networking"], req=["cdn"], pref=["egress", "cache"],
     plabel="per GB egress")
_add("Cloud NAT", "nfr", "gateway", "hour", 0.045, ["Networking"], req=["nat"], pref=["gateway", "nat"])
_add("Private Service Connect", "nfr", "endpoint", "hour", 0.01, ["Networking"], req=["private", "service", "connect"],
     pref=["endpoint"], aliases=["psc"])
_add("VPC Service Controls", "nfr", "perimeter", "month", 0.0, [], free=True, aliases=["vpc-sc", "vpc sc"])
_add("Cloud IAM & Workload Identity Federation", "nfr", "project", "month", 0.0, [], free=True,
     aliases=["cloud iam", "iam", "workload identity federation"])
_add("Cloud KMS", "nfr", "key version", "month", 0.06, ["Cloud Key Management Service (KMS)", "Cloud KMS"],
     pref=["key", "version", "software"], aliases=["kms", "cloud key management service"])
_add("Secret Manager", "nfr", "secret version", "month", 0.06, ["Secret Manager"], pref=["active", "secret", "version"])
_add("Sensitive Data Protection (DLP)", "nfr", "job", "usage", 1.00, ["Sensitive Data Protection", "Cloud Data Loss Prevention (DLP)", "Cloud DLP"],
     pref=["inspection", "inspect", "storage"], plabel="per GB inspected", aliases=["dlp", "cloud dlp", "data loss prevention"])
_add("Security Command Center", "nfr", "organization", "usage", 0.0, ["Security Command Center"], pref=["premium", "standard"],
     plabel="tier-based (see GCP)", aliases=["scc"])
_add("Model Armor", "nfr", "template", "usage", 1.50, ["Model Armor"], pref=["token", "prompt"],
     plabel="per 1M tokens screened", aliases=["vertex ai safety filters", "safety filters"])
_add("Vertex AI Model Monitoring", "nfr", "monitor", "usage", 3.50, ["Vertex AI"], pref=["monitoring", "model"],
     plabel="per GB analyzed")
_add("Dataplex", "nfr", "lake", "usage", 0.06, ["Dataplex"], pref=["processing", "dcu", "standard"],
     plabel="per DCU-hour", aliases=["dataplex governance", "data catalog"])
_add("Cloud Monitoring", "nfr", "workspace", "usage", 0.258, ["Cloud Monitoring", "Stackdriver Monitoring"], pref=["metric", "ingested", "mib"],
     plabel="per MiB ingested", aliases=["monitoring"])
_add("Cloud Logging", "nfr", "log bucket", "usage", 0.50, ["Cloud Logging", "Stackdriver Logging"], pref=["log", "ingested", "storage"],
     plabel="per GiB ingested", aliases=["logging"])
_add("Cloud Trace", "nfr", "project", "usage", 0.20, ["Cloud Trace", "Stackdriver Trace"], pref=["span", "ingested"],
     plabel="per 1M spans", aliases=["trace"])
_add("Backup and DR Service", "nfr", "vault", "usage", 0.05, ["Backup and DR Service", "Backup and DR"], pref=["backup", "stored", "storage"],
     plabel="per GB-month", aliases=["backup and dr", "backup", "disaster recovery"])

# ---------------------------------------------------------------- more reference-architecture services
# static=None means "no reliable fixed list price": the row shows "see GCP pricing" instead of a guess.
_add("Firebase Hosting", "fixed", "site", "usage", 0.15, ["Firebase Hosting"], pref=["transfer", "storage"],
     plabel="per GB transferred", aliases=["firebase hosting web channel"])
_add("Firebase Cloud Messaging", "fixed", "project", "month", 0.0, [], free=True, aliases=["fcm", "firebase messaging"])
_add("CCAI Platform", "fixed", "agent seat", "usage", None, [], plabel="per agent seat (see GCP pricing)",
     aliases=["ccai", "contact center ai platform", "contact center ai", "ccaas"])
_add("Looker", "fixed", "instance", "usage", None, [], plabel="custom pricing (see GCP)",
     aliases=["looker (finance)", "looker studio pro"])
_add("Application Integration", "fixed", "integration", "usage", None, ["Application Integration"], plabel="per execution (see GCP pricing)",
     aliases=["app integration", "application integration (rpa)"])
_add("Integration Connectors", "fixed", "connection node", "hour", 0.70, ["Integration Connectors"], pref=["connection", "node"],
     aliases=["integration connectors (mcp)", "mcp connectors", "connectors"])
_add("Gen AI Evaluation Service", "fixed", "evaluation job", "usage", None, [], plabel="usage-based (see GCP pricing)",
     aliases=["gen ai eval service", "vertex ai evaluation"])
_add("Vertex AI Model Garden", "fixed", "model", "usage", None, [], plabel="depends on the model (see GCP pricing)",
     aliases=["model garden", "foundation model gateway"])
_add("Vertex AI Training Job", "fixed", "training job", "usage", None, [], plabel="per node-hour of training (see GCP pricing)",
     aliases=["vertex ai training", "model training"])
_add("Vertex AI AutoML", "fixed", "model", "usage", None, [], plabel="per node-hour (see GCP pricing)", aliases=["automl"])
_add("BigQuery ML", "fixed", "model", "usage", None, [], plabel="usage-based (see GCP pricing)", aliases=["bqml"])
_add("Vertex AI Memory Bank", "fixed", "memory store", "usage", None, [], plabel="usage-based (see GCP pricing)",
     aliases=["memory bank", "agent memory"])
_add("Code Execution Sandbox", "fixed", "sandbox", "usage", None, [], plabel="usage-based (see GCP pricing)",
     aliases=["code execution gemini", "vertex ai code interpreter", "code interpreter", "code execution"])
_add("Google Distributed Cloud", "fixed", "cluster", "usage", None, [], plabel="custom pricing (see GCP)",
     aliases=["distributed cloud", "anthos", "cloud run for anthos"])

_add("Vertex AI Model Registry", "nfr", "registry", "month", 0.0, [], free=True, aliases=["model registry"])
_add("Vertex AI Model Cards", "nfr", "model card", "month", 0.0, [], free=True, aliases=["model cards"])
_add("Fairness Indicators", "nfr", "evaluation", "month", 0.0, [], free=True)
_add("Vertex AI Agent Policy Gating", "nfr", "policy", "month", 0.0, [], free=True, aliases=["agent policy gating", "policy gating"])
_add("Cloud Billing & Recommender", "nfr", "billing account", "month", 0.0, [], free=True,
     aliases=["cloud billing", "recommender", "cloud billing / recommender", "finops"])
_add("Data Catalog", "nfr", "catalog", "month", 0.0, [], free=True, aliases=["data catalog / lifecycle"])
_add("Artifact Analysis", "nfr", "image scan", "usage", 0.26, ["Artifact Analysis", "Container Analysis"], pref=["scan", "image"],
     plabel="per image scanned", aliases=["artifact analysis (sbom & binary authorization)", "binary authorization", "container analysis"])
_add("Isolated Code Sandbox (gVisor)", "nfr", "instance", "shape", None, ["Cloud Run"], shape="cloudrun",
     static_cpu=0.009, static_ram=0.001, aliases=["gvisor", "gvisor / cloud run isolated sandbox", "isolated sandbox"])

_BY_LOWER = {}
for _n, _s in CATALOG.items():
    _BY_LOWER[_n.lower()] = _n
    for _a in _s["aliases"]:
        _BY_LOWER[_a.lower()] = _n


def canonical_service(name: str):
    """Exact catalog name for what the LLM wrote (case/alias tolerant), else None."""
    return _BY_LOWER.get(" ".join(name.lower().split()))


# ---------------------------------------------------------------- reference-architecture layers
# Taken from the IBM L3 Component Overview (GCP view). "fr" layers hold the functional solution;
# "nfr" layers are the cross-cutting Security & Governance groups (plus operations).
LAYERS = [
    dict(id="users", name="User", section="USERS", kind="fr",
         purpose="Human and system consumers of the platform",
         ref="Identity Platform / Firebase Auth, Cloud Identity, Workforce IDP, IAP"),
    dict(id="channels", name="Channels", section="ENGAGEMENT", kind="fr",
         purpose="Web, mobile, voice and co-pilot channels users interact through",
         ref="Firebase Hosting, Firebase Cloud Messaging, Cloud Run, Dialogflow CX, CCAI, Speech-to-Text / Text-to-Speech, Vertex AI Agent Builder"),
    dict(id="process", name="Business Process - Workflows & Applications", section="ENGAGEMENT", kind="fr",
         purpose="Business processes, workflows and enterprise application integrations",
         ref="Cloud Workflows, Cloud Composer, Looker, Document AI, Application Integration"),
    dict(id="orchestration", name="Agentic Orchestration", section="MULTI AGENT SOLUTION", kind="fr",
         purpose="Plan, reason and orchestrate agents: task decomposition, skills, human-in-the-loop",
         ref="Vertex AI Agent Engine / Agent Builder, Vertex AI Gemini (reasoning), Gen AI Evaluation Service, Workflows + Firestore + Pub/Sub (HITL gateway)"),
    dict(id="tools", name="Tool & Integration", section="MULTI AGENT SOLUTION", kind="fr",
         purpose="Connect agents to enterprise tools, APIs and other agents using MCP / A2A and registries",
         ref="MCP servers on Cloud Run, A2A (Cloud Run + Apigee), Integration Connectors, Apigee, Apigee API Hub, Code Execution Sandbox"),
    dict(id="memory", name="Knowledge & Memory", section="MULTI AGENT SOLUTION", kind="fr",
         purpose="Session, long-term and vector memory that grounds agent reasoning",
         ref="Memorystore for Redis, Firestore, Vertex AI Memory Bank, Vertex AI Search / Vector Search"),
    dict(id="model", name="AI Model", section="MULTI AGENT SOLUTION", kind="fr",
         purpose="Foundation, generative and classical ML models and the gateway in front of them",
         ref="Vertex AI Gemini, Gemini Code Assist, Vertex AI AutoML, Model Garden, Training Job, BigQuery ML, model gateway"),
    dict(id="data", name="Enterprise Data & Systems", section="DATA", kind="fr",
         purpose="Systems of record and data stores the agents read from and act on",
         ref="Cloud SQL / AlloyDB, Firestore, Cloud Spanner, Vertex AI Vector Search, GCS + BigQuery, enterprise connectors"),
    dict(id="deploy", name="Deployment Layer", section="INFRASTRUCTURE", kind="fr",
         purpose="Where the platform runs: Kubernetes, serverless, hybrid; plus networking, CI/CD and eventing",
         ref="GKE, Cloud Run, Cloud Functions, Compute Engine, Cloud Load Balancing, Cloud DNS, Artifact Registry, Cloud Build, Distributed Cloud"),

    dict(id="sec_identity", name="Identity & Delegation", section="SECURITY", kind="nfr",
         purpose="Who/what may act (engagement and multi-agent layers)",
         ref="Cloud IAM & Workload Identity Federation"),
    dict(id="sec_adversarial", name="Adversarial AI & Model Defense", section="SECURITY", kind="nfr",
         purpose="Protect agents and models from prompt attacks and unsafe output (agentic and AI model layers)",
         ref="Model Armor / Vertex AI Safety Filters, Vertex AI Agent Policy Gating"),
    dict(id="sec_sandbox", name="Tool & Runtime Sandboxing", section="SECURITY", kind="nfr",
         purpose="Isolate tool and code execution (tool and integration layer)",
         ref="Isolated Code Sandbox (gVisor / Cloud Run)"),
    dict(id="sec_data", name="Data, Secrets & Privacy", section="SECURITY", kind="nfr",
         purpose="Keys, secrets, PII protection and data access control (knowledge and enterprise data layers)",
         ref="Cloud KMS, Secret Manager, Sensitive Data Protection (DLP)"),
    dict(id="sec_perimeter", name="Perimeter & Threat Posture", section="SECURITY", kind="nfr",
         purpose="Network perimeter, WAF and threat detection (deployment / infra layer)",
         ref="Private Service Connect, VPC Service Controls, Cloud Armor, Cloud NAT, Artifact Analysis, Security Command Center"),
    dict(id="gov_access", name="Access & Model Registry", section="GOVERNANCE", kind="nfr",
         purpose="Access control and registries for models and agents (users and AI model layers)",
         ref="Vertex AI Model Registry, Apigee API Hub as agent registry"),
    dict(id="gov_responsible", name="Responsible AI & Quality", section="GOVERNANCE", kind="nfr",
         purpose="Model quality, fairness, drift and AI governance (multi-agent AI and knowledge layers)",
         ref="Vertex AI Model Cards, Fairness Indicators, Vertex AI Model Monitoring, Dataplex AI governance"),
    dict(id="gov_finops", name="FinOps & Data Lifecycle", section="GOVERNANCE", kind="nfr",
         purpose="Cost control, data catalog/lifecycle, backup and disaster recovery (data and infra layers)",
         ref="Cloud Billing / Recommender, Data Catalog, Backup and DR Service"),
    dict(id="ops", name="Operations, Observability & Performance", section="OPERATIONS", kind="nfr",
         purpose="Monitoring, logging, tracing and edge performance (AgentOps)",
         ref="Cloud Monitoring, Cloud Logging, Cloud Trace, Cloud CDN"),
]
LAYER_BY_ID = {l["id"]: l for l in LAYERS}
_LAYER_BY_NAME = {l["name"].lower(): l["id"] for l in LAYERS}

# Where a service belongs when the LLM gives no (or an invalid) layer.
DEFAULT_LAYER = {
    "Google Kubernetes Engine (cluster)": "deploy", "Compute Engine VM": "deploy", "Cloud Run (min instances)": "deploy",
    "MCP Server (Cloud Run)": "tools", "Cloud Functions": "deploy", "Cloud SQL": "data", "AlloyDB": "data",
    "Cloud Spanner": "data", "Firestore": "memory", "Memorystore for Redis": "memory", "Vertex AI Vector Search": "memory",
    "Vertex AI Agent Engine": "orchestration", "Vertex AI Gemini (LLM)": "model", "Vertex AI Search": "memory",
    "Vertex AI Prediction Endpoint": "model", "Dialogflow CX": "channels", "Document AI": "process",
    "Speech-to-Text": "channels", "Text-to-Speech": "channels", "Apigee": "tools", "Cloud Composer": "process",
    "Cloud Workflows": "process", "Pub/Sub": "orchestration", "Cloud Scheduler": "process", "Cloud Storage": "data",
    "BigQuery": "data", "Artifact Registry": "deploy", "Cloud Build": "deploy", "Cloud Load Balancing": "deploy",
    "Cloud DNS": "deploy", "Identity Platform": "users", "Firebase Hosting": "channels",
    "Firebase Cloud Messaging": "channels", "CCAI Platform": "channels", "Looker": "process",
    "Application Integration": "process", "Integration Connectors": "tools", "Gen AI Evaluation Service": "orchestration",
    "Vertex AI Model Garden": "model", "Vertex AI Training Job": "model", "Vertex AI AutoML": "model",
    "BigQuery ML": "model", "Vertex AI Memory Bank": "memory", "Code Execution Sandbox": "tools",
    "Google Distributed Cloud": "deploy",
    "Cloud Armor": "sec_perimeter", "Cloud CDN": "ops", "Cloud NAT": "sec_perimeter",
    "Private Service Connect": "sec_perimeter", "VPC Service Controls": "sec_perimeter",
    "Cloud IAM & Workload Identity Federation": "sec_identity", "Cloud KMS": "sec_data", "Secret Manager": "sec_data",
    "Sensitive Data Protection (DLP)": "sec_data", "Security Command Center": "sec_perimeter",
    "Model Armor": "sec_adversarial", "Vertex AI Model Monitoring": "gov_responsible", "Dataplex": "gov_responsible",
    "Cloud Monitoring": "ops", "Cloud Logging": "ops", "Cloud Trace": "ops", "Backup and DR Service": "gov_finops",
    "Vertex AI Model Registry": "gov_access", "Vertex AI Model Cards": "gov_responsible",
    "Fairness Indicators": "gov_responsible", "Vertex AI Agent Policy Gating": "sec_adversarial",
    "Cloud Billing & Recommender": "gov_finops", "Data Catalog": "gov_finops", "Artifact Analysis": "sec_perimeter",
    "Isolated Code Sandbox (gVisor)": "sec_sandbox",
}


def normalize_layer(layer: str, service: str) -> str:
    """Layer id for a component: the LLM's choice if it is a valid layer of the right kind, else the service default."""
    group = CATALOG[service]["group"]
    want = "fr" if group == "fixed" else "nfr"
    key = (layer or "").strip().lower()
    lid = key if key in LAYER_BY_ID else _LAYER_BY_NAME.get(key)
    if lid and LAYER_BY_ID[lid]["kind"] == want:
        return lid
    return DEFAULT_LAYER.get(service) or ("deploy" if want == "fr" else "ops")
