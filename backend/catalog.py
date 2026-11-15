"""GCP service catalog: the services the LLM may choose from and how each one is priced.

group : "fixed" -> fixed infrastructure & platform services table
        "nfr"   -> non-functional components table (security, resilience, observability)
mode  : "hour"  qty x hours x price per unit-hour
        "shape" qty (instances) x hours x (vCPU x cpu_hr + RAM GiB x ram_hr)
        "month" qty x flat monthly price
        "usage" LLM-estimated monthly volume x price per usage unit (see USAGE_UNITS)
catalog : Cloud Billing Catalog display-name candidates (first match wins)
req/pref: description tokens a SKU must contain (req) / is ranked higher for (pref)
excl    : description tokens that rule a SKU out (usage mode: sibling SKUs billed differently)
static  : approximate list price (USD) used only when the live catalog gives no match
web     : public GCP list-price page the static price comes from (shown as the row source instead of "approx")
"""

CATALOG: dict = {}


def _add(name, group, unit, mode, static, catalog, req=(), pref=(), plabel=None, aliases=(), excl=(), **extra):
    CATALOG[name] = dict(group=group, unit=unit, mode=mode, static=static, catalog=list(catalog),
                         req=list(req), pref=list(pref), plabel=plabel, aliases=list(aliases), excl=list(excl), **extra)


# ---------------------------------------------------------------- fixed / platform
_add("Google Kubernetes Engine (cluster)", "fixed", "cluster", "hour", 0.10, ["Kubernetes Engine"],
     pref=["cluster", "management", "fee"], aliases=["gke", "google kubernetes engine", "gke cluster"])
_add("Compute Engine VM", "fixed", "VM", "shape", None, ["Compute Engine"], shape="compute",
     static_cpu=0.0335, static_ram=0.0045, aliases=["compute engine", "gce", "gke node pool", "gke nodes"])
_add("Cloud Run (min instances)", "fixed", "instance", "shape", None, ["Cloud Run"], shape="cloudrun",
     static_cpu=0.009, static_ram=0.001, aliases=["cloud run", "cloud run service"])
_add("MCP Server (Cloud Run)", "fixed", "instance", "shape", None, ["Cloud Run"], shape="cloudrun",
     static_cpu=0.009, static_ram=0.001, aliases=["mcp server", "mcp servers", "custom mcp server"])
_add("Cloud Functions", "fixed", "function", "usage", 0.40, ["Cloud Run Functions", "Cloud Functions"], pref=["invocations"],
     plabel="per 1M invocations", aliases=["cloud functions (2nd gen)"])
_add("Cloud SQL", "fixed", "instance", "shape", None, ["Cloud SQL"], shape="cloudsql",
     static_cpu=0.0413, static_ram=0.007, aliases=["cloud sql for postgresql", "cloud sql postgresql", "postgresql"])
_add("AlloyDB", "fixed", "instance", "shape", None, ["AlloyDB for PostgreSQL", "AlloyDB"], shape="alloydb",
     static_cpu=0.0661, static_ram=0.0112, aliases=["alloydb for postgresql"])
# AlloyDB bills cluster storage apart from vCPU / RAM (like Cloud SQL Storage): usage = GB stored
_add("AlloyDB Storage", "fixed", "cluster", "usage", 0.30, ["AlloyDB for PostgreSQL", "AlloyDB"], req=["cluster", "database", "storage"],
     pref=["cluster", "database", "storage"], plabel="per GB-month", excl=["express", "free", "backup"],
     aliases=["alloydb database storage", "alloydb disk"])
# Database storage is billed apart from vCPU / RAM (the Azure SQL line carries "250 GB Storage"); usage = GB stored.
# ha_aware: an "HA" sku_tier on the row prices the Regional (replicated) storage SKU, otherwise Zonal.
_add("Cloud SQL Storage", "fixed", "instance", "usage", 0.17, ["Cloud SQL"], req=["storage"],
     pref=["postgresql", "standard", "ssd"], plabel="per GB-month", ha_aware=True,
     excl=["fdc", "trial", "hyperdisk", "iops", "low", "plus", "free", "backup", "cache", "extended"],
     aliases=["cloud sql ssd storage", "database storage", "cloud sql disk"])
_add("Cloud Spanner", "fixed", "node", "hour", 0.90, ["Cloud Spanner"], pref=["node", "regional"],
     aliases=["spanner"])
_add("Firestore", "fixed", "database", "usage", 0.06, ["Cloud Firestore", "Firestore"], pref=["read", "ops"],
     plabel="per 100K reads", excl=["enterprise"])
_add("Memorystore for Redis", "fixed", "GB", "hour", 0.05, ["Cloud Memorystore for Redis", "Memorystore for Redis"],
     pref=["capacity", "m1"], aliases=["memorystore", "redis"])  # M1 = 1-4 GB band; Basic/Standard comes from sku_tier
_add("Vertex AI Vector Search", "fixed", "node", "hour", 0.75, ["Vertex AI"],
     pref=["vector", "search", "index", "serving"], aliases=["vector search", "matching engine"])
_add("Vertex AI Agent Engine", "fixed", "agent runtime", "usage", 0.0864, ["Vertex AI"],
     pref=["agent", "engine", "runtime"], plabel="per vCPU-hour", aliases=["agent engine", "vertex ai agent builder", "agent builder"])
_GEMINI_EXCL = ["caching", "cache", "long", "priority", "video", "audio", "image", "live", "embedding", "batch", "tuning",
                "evaluation", "garden"]
# Gemini is billed per token and input / output are separate SKUs, so they are two rows (same model in sku_tier).
_add("Vertex AI Gemini (LLM)", "fixed", "model endpoint", "usage", 1.25, ["Vertex AI", "Generative Language API"], req=["input"],
     pref=["gemini", "ga", "text", "predictions"], plabel="per 1M input tokens", aliases=["gemini", "vertex ai gemini", "gemini api", "gemini input tokens"],
     excl=_GEMINI_EXCL)
_add("Vertex AI Gemini Output (LLM)", "fixed", "model endpoint", "usage", 10.00, ["Vertex AI", "Generative Language API"], req=["output"],
     pref=["gemini", "ga", "text", "predictions"], plabel="per 1M output tokens",
     aliases=["gemini output", "gemini output tokens", "vertex ai gemini output"], excl=_GEMINI_EXCL + ["thinking"])
_add("Vertex AI Embeddings", "fixed", "model endpoint", "usage", 0.15, ["Vertex AI"], req=["embedding"],
     pref=["large", "text", "predictions"], plabel="per 1M embedding tokens",
     aliases=["text embeddings", "gemini embedding", "embeddings", "text embedding"],
     excl=["multimodal", "memory", "bank", "batch", "image", "video", "mm"])
_add("Vertex AI Search", "fixed", "app", "usage", 4.00, ["Discovery Engine", "Vertex AI Search"], req=["request", "count"],
     pref=["search", "enterprise"], plabel="per 1K queries", aliases=["vertex ai search and conversation", "discovery engine"],
     excl=["healthcare", "media", "recommendations", "llm", "generative", "configurable", "layout", "optical", "gemini"])
_add("Vertex AI Prediction Endpoint", "fixed", "node", "hour", 0.60, ["Vertex AI"],
     pref=["prediction", "online", "node"], aliases=["vertex ai endpoint", "model endpoint"])
_add("Dialogflow CX", "fixed", "agent", "usage", 7.00, ["Cloud Dialogflow API", "Dialogflow"], pref=["cx", "text", "query", "request"],
     plabel="per 1K requests", aliases=["dialogflow"], excl=["session"])  # session SKUs are billed per session, not request
_add("Document AI", "fixed", "processor", "usage", 1.50, ["Document AI", "Cloud Document AI"], pref=["page", "ocr"],
     plabel="per 1K pages")
_add("Speech-to-Text", "fixed", "service", "usage", 0.024, ["Cloud Speech API"], req=["audio", "length"], pref=["standard"],
     plabel="per minute of audio", excl=["logged", "premium", "medical", "dynamic", "batch"], aliases=["speech to text", "stt"])
_add("Text-to-Speech", "fixed", "service", "usage", 16.00, ["Cloud Text-to-Speech", "Text-to-Speech"], pref=["character", "standard", "wavenet"],
     plabel="per 1M characters", aliases=["text to speech", "tts"])
_add("Apigee", "fixed", "environment", "hour", 0.50, ["Apigee"], pref=["environment", "pay", "go"],
     aliases=["apigee x", "apigee api hub"])
_add("Cloud Composer", "fixed", "environment", "hour", 0.35, ["Cloud Composer"], pref=["small", "environment", "composer"],
     aliases=["composer"])
_add("Cloud Workflows", "fixed", "workflow", "usage", 0.01, ["Workflows", "Cloud Workflows"], pref=["step", "internal", "external"],
     plabel="per 1K steps", aliases=["workflows"])
_add("Pub/Sub", "fixed", "topic", "usage", 40.00, ["Cloud Pub/Sub", "Pub/Sub"], pref=["message", "delivery", "throughput"],
     plabel="per TiB", aliases=["pubsub", "cloud pub/sub", "cloud pubsub"])
# Products GCP sells that an order-status support agent needs. Live Cloud Billing SKU first; when no SKU matches,
# the public GCP list-price page named in "web" is used and the row's source says so (never a silent guess).
_add("API Gateway", "fixed", "gateway", "usage", 3.00, ["API Gateway"], req=["call"], pref=["api", "gateway", "calls"],
     plabel="per 1M API calls", web="cloud.google.com/api-gateway/pricing",  # $3.00 per 1M calls, first 2M free (not modelled)
     aliases=["gcp api gateway"])
_add("Application Integration", "fixed", "integration", "usage", 0.50, ["Application Integration"], req=["flow", "execution"],
     pref=["integration", "execution", "flow"], plabel="per 1K integration executions",
     web="cloud.google.com/application-integration/pricing",  # $0.50 per 1,000 executions
     aliases=["app integration"])
_add("CCAI Platform", "fixed", "agent seat", "month", 135.00, ["Cloud Contact Center AI Platform"], req=["named", "user"],
     pref=["named", "user", "digital", "voice"], plabel="per named user per month", bad_ok=("license",),
     excl=["cobrowse", "insights", "add-on"], web="cloud.google.com/contact-center/ccai-platform/pricing",  # $135 named user, pay as you go
     aliases=["ccai", "cloud ccai", "contact center ai platform", "co-pilot chat"])
_add("Security Command Center", "nfr", "subscription", "month", 15000.0 / 12, [], web="cloud.google.com/security-command-center/pricing",
     aliases=["scc", "security command center (scc)", "security command ctr"])  # Premium: $15,000 a year minimum; no per-environment SKU
_add("Vertex AI Memory Bank", "fixed", "memory bank", "usage", 0.30, ["Vertex AI"], req=["agent", "storage"],
     pref=["agent", "platform", "storage"], plabel="per GiB-month stored", web="cloud.google.com/vertex-ai/pricing",  # Agent Platform Storage $0.30/GiB-month
     aliases=["memory bank", "agent memory bank", "agent platform memory bank"])

_add("Cloud Scheduler", "fixed", "job", "month", 0.10, ["Cloud Scheduler"], req=["jobs"], pref=["jobs"], count_month=31)  # SKU is per job-day
_add("Cloud Storage", "fixed", "bucket", "usage", 0.023, ["Cloud Storage"], pref=["standard", "storage"],
     plabel="per GB-month", aliases=["gcs", "cloud storage bucket"])
_add("BigQuery", "fixed", "dataset", "usage", 6.25, ["BigQuery"], pref=["analysis", "query", "queries"],
     plabel="per TiB scanned", aliases=["bigquery dataset"])
_add("Artifact Registry", "fixed", "repository", "usage", 0.10, ["Artifact Registry"], pref=["storage"],
     plabel="per GB-month")
_add("Cloud Build", "fixed", "pipeline", "usage", 0.003, ["Cloud Build"], pref=["build", "time", "e2", "standard"],
     plabel="per build-minute", excl=["ram", "cpu", "utilization", "transfer"], aliases=["cloud build pipeline"])
_add("Cloud Load Balancing", "fixed", "forwarding rule", "hour", 0.025, ["Networking"],
     req=["forwarding", "rule"], pref=["load", "balancing", "application"], aliases=["load balancer", "external application load balancer", "https load balancer"])
_add("Cloud DNS", "fixed", "managed zone", "month", 0.20, ["Cloud DNS"], pref=["zone", "managed"])
_add("Identity Platform", "fixed", "tenant", "usage", 0.0055, ["Identity Platform", "Identity Toolkit"], pref=["monthly", "active", "users"],
     plabel="per MAU", aliases=["firebase auth", "firebase authentication"])

# Every GCP product the knowledge base names is here, so any use case can be costed: live SKU first, public GCP page second.
# Model Garden (open / partner models as a service): one per-token SKU per model, so every word of the model in sku_tier
# must be in the SKU; with no match the price cells stay empty (another model's price is never used).
_MG_EXCL = ["batch", "cached", "cache", "fine", "tuning", "provisioned", "thinking"]
_add("Vertex AI Model Garden (LLM)", "fixed", "model endpoint", "usage", None, ["Vertex AI"], req=["garden", "input"],
     pref=["garden", "service"], plabel="per 1M input tokens", excl=_MG_EXCL, tier_any=True,
     aliases=["model garden", "vertex ai model garden", "model garden input tokens", "model garden maas"])
_add("Vertex AI Model Garden Output (LLM)", "fixed", "model endpoint", "usage", None, ["Vertex AI"], req=["garden", "output"],
     pref=["garden", "service"], plabel="per 1M output tokens", excl=_MG_EXCL, tier_any=True,
     aliases=["model garden output", "model garden output tokens", "vertex ai model garden output"])
# Gen AI Evaluation Service: model-judged metrics billed per input / output token
_add("Gen AI Evaluation Service", "fixed", "evaluation", "usage", 0.03, ["Vertex AI"], req=["evaluation", "service", "input"],
     pref=["automatic", "metric"], plabel="per 1M input tokens", web="cloud.google.com/vertex-ai/generative-ai/pricing",
     aliases=["gen ai eval service", "vertex ai evaluation", "evaluation service"])
_add("Gen AI Evaluation Service Output", "fixed", "evaluation", "usage", 0.09, ["Vertex AI"], req=["evaluation", "service", "output"],
     pref=["automatic", "metric"], plabel="per 1M output tokens", web="cloud.google.com/vertex-ai/generative-ai/pricing",
     aliases=["gen ai eval service output", "evaluation service output"])
# Training jobs / pipelines bill the machine's vCPUs and RAM separately: usage = vCPU-hours, and GiB-hours on the RAM row.
_TRAIN_EXCL = ["management", "fee", "reduction", "preemptible", "a2", "a3", "optimized", "tpu"]
_add("Vertex AI Training Job", "fixed", "training run", "usage", 0.0437, ["Vertex AI"], req=["training", "pipelines", "core"],
     pref=["predefined", "n1"], plabel="per vCPU-hour", excl=_TRAIN_EXCL, web="cloud.google.com/vertex-ai/pricing",
     aliases=["vertex ai training", "custom training", "model training job", "vertex ai training job vcpu"])
_add("Vertex AI Training Job RAM", "fixed", "training run", "usage", 0.0059, ["Vertex AI"], req=["training", "pipelines", "ram"],
     pref=["predefined", "n1"], plabel="per GiB-hour", excl=_TRAIN_EXCL, web="cloud.google.com/vertex-ai/pricing",
     aliases=["vertex ai training ram", "custom training ram"])
# AutoML: node-hours; the data type and stage in sku_tier (e.g. "Image Classification Training") pick the SKU.
_add("Vertex AI AutoML", "fixed", "automl job", "usage", None, ["Vertex AI"], req=["automl"], pref=["training"],
     plabel="per node-hour", tier_any=True, excl=["device", "operations", "predictions"],
     aliases=["automl", "vertex automl"])
# BigQuery ML has no SKU of its own in the catalogue; its prices are on the BigQuery pricing page (on-demand, per TiB processed).
_add("BigQuery ML", "fixed", "model", "usage", 6.25, [], plabel="per TiB scanned", web="cloud.google.com/bigquery/pricing",
     aliases=["bqml", "bigquery ml prediction"])  # evaluation, prediction and external-model creation
_add("BigQuery ML Training", "fixed", "model", "usage", 312.50, [], plabel="per TiB scanned", web="cloud.google.com/bigquery/pricing",
     aliases=["bqml training", "bigquery ml model creation"])  # built-in model creation (regression, k-means, PCA, time series)
# Looker (Google Cloud core): sku_tier picks the SKU - "Standard Edition", "Standard User", "Developer User" or "Viewer User".
_add("Looker", "fixed", "edition / user", "month", 5000.0, ["Looker"], req=["looker"], pref=["edition"],
     excl=["trial"], count_month=1, web="cloud.google.com/looker/pricing", aliases=["looker (google cloud core)", "looker finance"])
# Google Distributed Cloud / GKE Enterprise: per vCPU-hour (sku_tier "Bare Metal" or "vSphere").
_add("Google Distributed Cloud", "fixed", "vCPU", "hour", 0.03288, ["GKE Enterprise / GDC"], pref=["gdc"],
     excl=["trial", "apigee", "multicloud", "aws", "azure", "edge", "appliance"], web="cloud.google.com/kubernetes-engine/enterprise/pricing",
     aliases=["gdc", "anthos", "gke enterprise", "distributed cloud", "gke on-prem", "gdc bare metal"])
# Gemini Code Assist: per licensed user, monthly commitment (no Cloud Billing SKU)
_add("Gemini Code Assist", "fixed", "user licence", "month", 22.80, [], web="cloud.google.com/products/gemini/pricing",
     aliases=["code assist", "gemini code assist standard", "coding agent"])  # $0.031232877 per hour
_add("Gemini Code Assist Enterprise", "fixed", "user licence", "month", 54.00, [], web="cloud.google.com/products/gemini/pricing",
     aliases=["code assist enterprise"])  # $0.073972603 per hour
# Sandbox for model-written code (Code Execution): vCPU-hours at the Agent Platform Compute rate.
_add("Code Execution Sandbox", "nfr", "sandbox", "usage", 0.085, ["Vertex AI"], req=["agent", "compute"], pref=["compute"], plabel="per vCPU-hour",
     web="cloud.google.com/vertex-ai/pricing", aliases=["code execution", "gemini code execution", "agent sandbox", "agent runtime sandbox"])

# ---------------------------------------------------------------- non-functional
_add("Cloud Armor", "nfr", "security policy", "month", 5.00, ["Cloud Armor", "Networking"],
     req=["armor"], pref=["policy", "security"], aliases=["cloud armor waf", "waf"])
_add("Cloud CDN", "nfr", "origin", "usage", 0.08, ["Networking"], req=["cdn"], pref=["egress", "cache"],
     plabel="per GB egress")
_add("Cloud NAT", "nfr", "gateway", "hour", 0.045, ["Networking"], req=["nat"], pref=["gateway", "nat"])
_add("Private Service Connect", "nfr", "endpoint", "hour", 0.01, ["Networking"], req=["private", "service", "connect", "end", "point"],
     pref=["consumer"], aliases=["psc"])
_add("VPC Service Controls", "nfr", "perimeter", "month", 0.0, [], free=True, aliases=["vpc-sc", "vpc sc"])
_add("Cloud IAM & Workload Identity Federation", "nfr", "project", "month", 0.0, [], free=True,
     aliases=["cloud iam", "iam", "workload identity federation"])
_add("Cloud KMS", "nfr", "key version", "month", 0.06, ["Cloud Key Management Service (KMS)", "Cloud KMS"],
     pref=["key", "version", "software"], aliases=["kms", "cloud key management service"])
_add("Secret Manager", "nfr", "secret version", "month", 0.06, ["Secret Manager"], pref=["active", "secret", "version"])
_add("Sensitive Data Protection (DLP)", "nfr", "job", "usage", 3.00, ["Cloud Data Loss Prevention"], req=["inspected"],
     pref=["content"], excl=["hybrid"], plabel="per GB inspected",  # sku_tier "Storage" prices a storage scan instead of content
     aliases=["dlp", "cloud dlp", "data loss prevention"])
# Model Armor has no Cloud Billing SKU: $0.10 per 1M tokens screened (first 2M a month free, not modelled)
_add("Model Armor", "nfr", "template", "usage", 0.10, [], plabel="per 1M tokens screened",
     web="cloud.google.com/security-command-center/pricing", aliases=["vertex ai safety filters", "safety filters"])
_add("Vertex AI Model Monitoring", "nfr", "monitor", "usage", 3.50, ["Vertex AI"], pref=["monitoring", "model"],
     plabel="per GB analyzed")
_add("Dataplex", "nfr", "lake", "usage", 0.06, ["Dataplex"], req=["processing", "dcu"], pref=["processing"],
     plabel="per DCU-hour", excl=["premium"], aliases=["dataplex governance", "data catalog"])  # SKU is per milli-DCU-hour
_add("Cloud Monitoring", "nfr", "workspace", "usage", 0.258, ["Cloud Monitoring", "Stackdriver Monitoring"], pref=["metric", "ingested", "mib"],
     plabel="per MiB ingested", aliases=["monitoring"])
_add("Cloud Logging", "nfr", "log bucket", "usage", 0.50, ["Cloud Logging", "Stackdriver Logging"], pref=["log", "ingested", "storage"],
     plabel="per GiB ingested", aliases=["logging"])
_add("Cloud Trace", "nfr", "project", "usage", 0.20, ["Cloud Trace", "Stackdriver Trace"], pref=["span", "ingested"],
     plabel="per 1M spans", aliases=["trace"])
_add("Backup and DR Service", "nfr", "vault", "usage", 0.05, ["Backup and DR Service", "Backup and DR"], pref=["backup", "stored", "storage"],
     plabel="per GB-month", aliases=["backup and dr", "backup", "disaster recovery"])

# ---------------------------------------------------------------- more reference-architecture services
_add("Firebase Hosting", "fixed", "site", "usage", 0.15, ["Firebase Hosting"], req=["bandwidth"], pref=["outgoing", "bandwidth"],
     plabel="per GB transferred", aliases=["firebase hosting web channel"])
_add("Firebase Cloud Messaging", "fixed", "project", "month", 0.0, [], free=True, aliases=["fcm", "firebase messaging"])
_add("Integration Connectors", "fixed", "connection node", "hour", 0.70, ["Integration Connectors"], pref=["connection", "node"],
     aliases=["integration connectors (mcp)", "mcp connectors", "connectors"])
_add("Vertex AI Model Registry", "nfr", "registry", "month", 0.0, [], free=True, aliases=["model registry"])
_add("Vertex AI Model Cards", "nfr", "model card", "month", 0.0, [], free=True, aliases=["model cards"])
_add("Fairness Indicators", "nfr", "evaluation", "month", 0.0, [], free=True)
_add("Vertex AI Agent Policy Gating", "nfr", "policy", "month", 0.0, [], free=True, aliases=["agent policy gating", "policy gating"])
_add("Cloud Billing & Recommender", "nfr", "billing account", "month", 0.0, [], free=True,
     aliases=["cloud billing", "recommender", "cloud billing / recommender", "finops"])
_add("Data Catalog", "nfr", "catalog", "month", 0.0, [], free=True, aliases=["data catalog / lifecycle"])
_add("Artifact Analysis", "nfr", "image scan", "usage", 0.26, ["On-Demand Scanning", "Container Registry Vulnerability Scanning"], req=["scans"], pref=["scans"],
     plabel="per image scanned", aliases=["artifact analysis (sbom & binary authorization)", "binary authorization", "container analysis"])
_add("Isolated Code Sandbox (gVisor)", "nfr", "instance", "shape", None, ["Cloud Run"], shape="cloudrun",
     static_cpu=0.009, static_ram=0.001, aliases=["gvisor", "gvisor / cloud run isolated sandbox", "isolated sandbox"])

# Usage-mode billing units: plabel -> (Cloud Billing unit, how many of that unit make one plabel unit).
# A live SKU is used only if its usageUnit or baseUnit is that unit, so volume and price always share a unit.
# Only GCP products are in the catalogue, each with a Cloud Billing price, a published GCP list price, or free.
_GIB, _TIB = 2 ** 30, 2 ** 40
USAGE_UNITS = {
    "per 1M invocations": ("count", 1e6), "per 100K reads": ("count", 1e5), "per vCPU-hour": ("s", 3600),
    "per 1M input tokens": ("count", 1e6), "per 1K queries": ("count", 1e3), "per 1K requests": ("count", 1e3),
    "per 1K pages": ("count", 1e3), "per minute of audio": ("s", 60), "per 1M characters": ("count", 1e6),
    "per 1K steps": ("count", 1e3), "per TiB": ("By", _TIB), "per GB-month": ("GiBy.mo", 1), "per node-hour": ("s", 3600), "per GiB-hour": ("GiBy.h", 1),
    "per TiB scanned": ("By", _TIB), "per build-minute": ("s", 60), "per MAU": ("count", 1),
    "per GB egress": ("By", _GIB), "per GB inspected": ("By", _GIB), "per 1M tokens screened": ("count", 1e6),
    "per GB analyzed": ("By", _GIB), "per DCU-hour": ("s", 3.6e6), "per MiB ingested": ("By", 2 ** 20),
    "per GiB ingested": ("By", _GIB), "per 1M spans": ("count", 1e6), "per GB transferred": ("By", _GIB),
    "per image scanned": ("count", 1), "per 1M output tokens": ("count", 1e6), "per 1M embedding tokens": ("count", 1e6),
    "per 1M API calls": ("count", 1e6), "per 1K integration executions": ("count", 1e3), "per GiB-month stored": ("GiBy.mo", 1),
}


def usage_unit(name: str):
    """Unit the LLM estimates monthly volume in (e.g. "1M input tokens"), or None if not volume-priced."""
    s = CATALOG[name]
    return s["plabel"][4:] if s["mode"] == "usage" and s["plabel"] in USAGE_UNITS else None


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
         ref="Firebase Hosting, Firebase Cloud Messaging, Cloud Run, Dialogflow CX, CCAI Platform, Speech-to-Text / Text-to-Speech, Vertex AI Agent Builder"),
    dict(id="process", name="Business Process - Workflows & Applications", section="ENGAGEMENT", kind="fr",
         purpose="Business processes, workflows and enterprise application integrations",
         ref="Cloud Workflows, Cloud Composer, Document AI"),
    dict(id="orchestration", name="Agentic Orchestration", section="MULTI AGENT SOLUTION", kind="fr",
         purpose="Plan, reason and orchestrate agents: task decomposition, skills, human-in-the-loop",
         ref="Vertex AI Agent Engine / Agent Builder, Vertex AI Gemini (reasoning), Gen AI Evaluation Service, Gemini Code Assist, Workflows + Firestore + Pub/Sub (HITL gateway)"),
    dict(id="tools", name="Tool & Integration", section="MULTI AGENT SOLUTION", kind="fr",
         purpose="Connect agents to enterprise tools, APIs and other agents using MCP / A2A and registries",
         ref="MCP servers on Cloud Run, A2A (Cloud Run + Apigee), Integration Connectors, Apigee, Apigee API Hub, API Gateway"),
    dict(id="memory", name="Knowledge & Memory", section="MULTI AGENT SOLUTION", kind="fr",
         purpose="Session, long-term and vector memory that grounds agent reasoning",
         ref="Memorystore for Redis, Firestore, Vertex AI Memory Bank, Vertex AI Search / Vector Search"),
    dict(id="model", name="AI Model", section="MULTI AGENT SOLUTION", kind="fr",
         purpose="Foundation, generative and classical ML models and the gateway in front of them",
         ref="Vertex AI Gemini (input / output tokens), Model Garden, Vertex AI Embeddings, Prediction Endpoint, AutoML, Training Job, BigQuery ML"),
    dict(id="data", name="Enterprise Data & Systems", section="DATA", kind="fr",
         purpose="Systems of record and data stores the agents read from and act on",
         ref="Cloud SQL / AlloyDB, Firestore, Cloud Spanner, Vertex AI Vector Search, GCS + BigQuery, Looker, enterprise connectors"),
    dict(id="deploy", name="Deployment Layer", section="INFRASTRUCTURE", kind="fr",
         purpose="Where the platform runs: Kubernetes, serverless, hybrid; plus networking, CI/CD and eventing",
         ref="GKE, Google Distributed Cloud, Cloud Run, Cloud Functions, Compute Engine, Cloud Load Balancing, Cloud DNS, Artifact Registry, Cloud Build"),

    dict(id="sec_identity", name="Identity & Delegation", section="SECURITY", kind="nfr",
         purpose="Who/what may act (engagement and multi-agent layers)",
         ref="Cloud IAM & Workload Identity Federation"),
    dict(id="sec_adversarial", name="Adversarial AI & Model Defense", section="SECURITY", kind="nfr",
         purpose="Protect agents and models from prompt attacks and unsafe output (agentic and AI model layers)",
         ref="Model Armor / Vertex AI Safety Filters, Vertex AI Agent Policy Gating"),
    dict(id="sec_sandbox", name="Tool & Runtime Sandboxing", section="SECURITY", kind="nfr",
         purpose="Isolate tool and code execution (tool and integration layer)",
         ref="Isolated Code Sandbox (gVisor / Cloud Run), Code Execution Sandbox"),
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
    "Firebase Cloud Messaging": "channels", "Integration Connectors": "tools",
    "Cloud Armor": "sec_perimeter", "Cloud CDN": "ops", "Cloud NAT": "sec_perimeter",
    "Private Service Connect": "sec_perimeter", "VPC Service Controls": "sec_perimeter",
    "Cloud IAM & Workload Identity Federation": "sec_identity", "Cloud KMS": "sec_data", "Secret Manager": "sec_data",
    "Sensitive Data Protection (DLP)": "sec_data",
    "Model Armor": "sec_adversarial", "Vertex AI Model Monitoring": "gov_responsible", "Dataplex": "gov_responsible",
    "Cloud Monitoring": "ops", "Cloud Logging": "ops", "Cloud Trace": "ops", "Backup and DR Service": "gov_finops",
    "Vertex AI Model Registry": "gov_access", "Vertex AI Model Cards": "gov_responsible",
    "Fairness Indicators": "gov_responsible", "Vertex AI Agent Policy Gating": "sec_adversarial",
    "Cloud Billing & Recommender": "gov_finops", "Data Catalog": "gov_finops", "Artifact Analysis": "sec_perimeter",
    "Isolated Code Sandbox (gVisor)": "sec_sandbox",
    "Vertex AI Gemini Output (LLM)": "model", "Vertex AI Embeddings": "model",
    "Cloud SQL Storage": "data",
    "Vertex AI Model Garden (LLM)": "model", "Vertex AI Model Garden Output (LLM)": "model", "Vertex AI AutoML": "model",
    "Vertex AI Training Job": "model", "Vertex AI Training Job RAM": "model", "BigQuery ML": "model", "BigQuery ML Training": "model",
    "AlloyDB Storage": "data", "Gen AI Evaluation Service": "orchestration", "Gen AI Evaluation Service Output": "orchestration",
    "Gemini Code Assist": "orchestration", "Gemini Code Assist Enterprise": "orchestration", "Looker": "data",
    "Google Distributed Cloud": "deploy", "Code Execution Sandbox": "sec_sandbox",
    "API Gateway": "tools", "Application Integration": "process", "CCAI Platform": "channels",
    "Security Command Center": "sec_perimeter", "Vertex AI Memory Bank": "memory",
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
