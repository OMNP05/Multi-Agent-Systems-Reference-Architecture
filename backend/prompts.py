"""Knowledge-base loading and the strict prompt."""
import json
from pathlib import Path

from catalog import CATALOG, LAYERS, canonical_service  # noqa: F401  (canonical_service re-exported)
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
    "mcp_tools": ["order_lookup", "customer_search"],
    "components": [
        {"group": "fixed", "layer": "data", "service": "Cloud SQL",
         "sku_tier": "PostgreSQL, HA", "vcpu": 4, "ram_gb": 16, "qty": {e: 1 for e in ENVS}},
        {"group": "nfr", "layer": "sec_perimeter", "service": "Cloud Armor",
         "sku_tier": "WAF policy", "vcpu": 0, "ram_gb": 0, "qty": {e: 1 for e in ENVS}},
    ],
}


def _allowed_block() -> str:
    lines = {"fixed": [], "nfr": []}
    for name, s in CATALOG.items():
        lines[s["group"]].append(f"- {name} (count unit: {s['unit']})")
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
1. Choose ONLY services from the allowed list above, spelled exactly as written.
2. Be thorough and enterprise-level: include EVERY service the solution genuinely needs across all layers - channels and identity, agent platform / orchestration runtime, the LLM (model name in sku_tier), MCP servers and tool/API gateway, memory and knowledge stores, enterprise data, deployment and networking, CI/CD and registry, and eventing. Do not stop at the obvious ones.
3. Group "fixed" = the functional (FR) solution: components that deliver the use case, each placed in one of the FR layers. Group "nfr" = non-functional components that satisfy the NFRs, each placed in one of the NFR layers (security, governance, operations). Cover EVERY FR layer the use case touches and EVERY NFR layer, mapping each NFR component to the layer it protects or governs. Include a sensible enterprise baseline of "nfr" components even when the NFR text is short, and scale them to the stated NFRs (availability, latency, throughput, peak, RTO/RPO, compliance, data residency, retention).
4. Environments are exactly: {', '.join(ENVS)}. Give an integer count for each environment (0 if the component is not needed there). Non-production is normally smaller than PROD, and PROD has redundancy where the NFRs call for it.
5. "layer" must be exactly one layer id from the list above (an FR layer for group "fixed", an NFR layer for group "nfr"). "qty" is the NUMBER OF COMPONENTS of that service (instances / nodes / clusters / replicas / resources, in the count unit shown) per environment. Do not give reasons.
6. For compute and database services (Compute Engine VM, Cloud Run, MCP Server, Cloud SQL, AlloyDB) set "vcpu" and "ram_gb" for ONE instance. For everything else use 0.
7. sku_tier is a short concrete size / edition / model (e.g. "e2-standard-4", "PostgreSQL, HA", "Gemini 2.5 Flash", "Standard tier"). ONE sku_tier per row, applied to all environments. If environments need different sizes, use separate rows (the environments that do not use that size get 0).
8. Use region "{region}" unless the use case clearly needs another GCP region.
9. "mcp_tools" lists the MCP tools / tool endpoints this solution needs (short snake_case names, e.g. "order_lookup"). Put MCP server hosting in components using the "MCP Server (Cloud Run)" service.
10. "assumptions" lists the key sizing and design assumptions you made (short sentences).
11. Keep every text value short and plain: never use double quotes, backslashes or line breaks inside a value. The JSON must be valid and complete.
12. Respond with ONE JSON object and nothing else (no markdown, no prose). Shape:
{json.dumps(SCHEMA_EXAMPLE, indent=2)}"""
    user = f"Use case / functional requirement:\n{use_case.strip()}"
    user += f"\n\nNon-functional requirements:\n{nfr.strip() or '(none given - assume a standard enterprise baseline)'}"
    if previous_error:
        user += f"\n\nYour previous answer was rejected: {previous_error}\nReturn corrected JSON only."
    return system, user
