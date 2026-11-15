"""Builds docs/Pricing_Strategy_and_Calculations.pdf from the backend code.

The catalogue appendix and the worked example are computed by importing backend/ (catalog.py,
pricing.py, graph.py), so the PDF always matches the code. The worked example runs in static-price
mode (no API key, no network).   Run:  python docs/build_pricing_pdf.py
"""
import os
import sys
from pathlib import Path

os.environ["GCP_PRICING_API_KEY"] = ""  # worked example: static prices, no network
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from fpdf import FPDF  # noqa: E402
from fpdf.fonts import FontFace  # noqa: E402

import catalog  # noqa: E402
import graph  # noqa: E402
import pricing  # noqa: E402
from schemas import ENVS, BomRequest, LlmBom  # noqa: E402

OUT = ROOT / "docs" / "Pricing_Strategy_and_Calculations.pdf"
FONTS = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
BLUE, DARK, MUTED, LINE, SOFT = (26, 115, 232), (32, 33, 36), (95, 99, 104), (218, 220, 224), (232, 240, 254)
AMBER = (254, 247, 224)


class Doc(FPDF):
    def multi_cell(self, w, h=None, text="", *args, **kw):
        kw.setdefault("new_x", "LMARGIN")
        kw.setdefault("new_y", "NEXT")
        return super().multi_cell(w, h, text, *args, **kw)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("body", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, "GCP Enterprise BOM Agent  ·  Pricing strategy, calculations & catalogue", align="L")
        self.ln(8)

    def footer(self):
        self.set_y(-12)
        self.set_font("body", "", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, f"Page {self.page_no()}", align="R")

    # ---- building blocks -------------------------------------------------
    def h1(self, text):
        if self.get_y() > 60:
            self.add_page()
        self.set_font("body", "B", 17)
        self.set_text_color(*BLUE)
        self.multi_cell(0, 9, text)
        self.set_draw_color(*BLUE)
        self.set_line_width(0.6)
        self.line(self.l_margin, self.get_y() + 1, self.l_margin + 30, self.get_y() + 1)
        self.ln(5)

    def h2(self, text):
        if self.get_y() > self.h - 45:
            self.add_page()
        self.ln(2)
        self.set_font("body", "B", 12.5)
        self.set_text_color(*DARK)
        self.multi_cell(0, 7, text)
        self.ln(1)

    def p(self, text, size=10):
        self.set_font("body", "", size)
        self.set_text_color(*DARK)
        self.multi_cell(0, 5.2, text, markdown=True)
        self.ln(2)

    def bullets(self, items, size=10):
        self.set_font("body", "", size)
        self.set_text_color(*DARK)
        for it in items:
            self.cell(5, 5.2, "•")
            self.multi_cell(0, 5.2, it, markdown=True)
            self.ln(0.8)
        self.ln(1.5)

    def code(self, text, size=8.5):
        self.set_font("mono", "", size)
        self.set_fill_color(246, 248, 250)
        self.set_text_color(*DARK)
        self.multi_cell(0, 4.4, text, fill=True, padding=(3, 4))
        self.ln(3)

    def note(self, text, fill=SOFT):
        self.set_font("body", "", 9.5)
        self.set_fill_color(*fill)
        self.set_text_color(*DARK)
        self.multi_cell(0, 5, text, fill=True, markdown=True, padding=(3, 4))
        self.ln(3)

    def grid(self, rows, widths, size=8.5, head=True, align=None):
        self.set_font("body", "", size)
        self.set_text_color(*DARK)
        self.set_draw_color(*LINE)
        self.set_line_width(0.2)
        hs = FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=BLUE)
        with self.table(col_widths=widths, line_height=size * 0.52, headings_style=hs, first_row_as_headings=head,
                        text_align=align or "LEFT", borders_layout="HORIZONTAL_LINES",
                        cell_fill_color=(248, 249, 250), cell_fill_mode="ROWS", repeat_headings=1) as t:
            for r in rows:
                row = t.row()
                for c in r:
                    row.cell(str(c))
        self.ln(4)


# ---- the pipeline diagram ---------------------------------------------------
def flow(pdf):
    nodes = [("load_kb", "Read 3 KB files"), ("build_prompt", "System + user prompt"),
             ("call_llm", "LLM, temperature 0"), ("validate_json", "Schema + catalogue check"),
             ("fetch_prices", "Billing Catalog API"), ("calculate", "Monthly cost & totals")]
    w, h, gap = 26.5, 15, 3.6
    x0, y = pdf.l_margin, pdf.get_y() + 2
    for i, (name, sub) in enumerate(nodes):
        x = x0 + i * (w + gap)
        pdf.set_fill_color(*(SOFT if i < 4 else (230, 244, 234)))
        pdf.set_draw_color(*BLUE)
        pdf.rect(x, y, w, h, style="DF", round_corners=True, corner_radius=2)
        pdf.set_xy(x, y + 2.5)
        pdf.set_font("body", "B", 7.6)
        pdf.set_text_color(*DARK)
        pdf.cell(w, 4, name, align="C")
        pdf.set_xy(x, y + 7.5)
        pdf.set_font("body", "", 6.6)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(w, 3, sub, align="C", new_x="RIGHT", new_y="TOP")
        if i < len(nodes) - 1:
            ax = x + w
            pdf.set_draw_color(*MUTED)
            pdf.line(ax + 0.4, y + h / 2, ax + gap - 0.4, y + h / 2)
            pdf.line(ax + gap - 1.6, y + h / 2 - 1, ax + gap - 0.4, y + h / 2)
            pdf.line(ax + gap - 1.6, y + h / 2 + 1, ax + gap - 0.4, y + h / 2)
    # retry loop validate_json -> build_prompt
    vx, bx = x0 + 3 * (w + gap) + w / 2, x0 + 1 * (w + gap) + w / 2
    yb = y + h + 5
    pdf.set_draw_color(200, 80, 60)
    pdf.line(vx, y + h, vx, yb)
    pdf.line(vx, yb, bx, yb)
    pdf.line(bx, yb, bx, y + h + 0.4)
    pdf.line(bx - 1, y + h + 1.6, bx, y + h + 0.4)
    pdf.line(bx + 1, y + h + 1.6, bx, y + h + 0.4)
    pdf.set_xy(bx, yb + 0.5)
    pdf.set_font("body", "", 7)
    pdf.set_text_color(200, 80, 60)
    pdf.cell(vx - bx, 4, "invalid JSON / unknown service: retry with the error (max 3 attempts, then HTTP 422)", align="C")
    pdf.set_xy(pdf.l_margin, yb + 8)


# ---- worked example (computed by the real code) ---------------------------
def worked_example():
    E = lambda a, b, c, d: dict(zip(ENVS, (a, b, c, d)))  # noqa: E731
    comps = [
        dict(group="fixed", layer="deploy", service="Google Kubernetes Engine (cluster)", sku_tier="Regional cluster", qty=E(1, 1, 1, 1)),
        dict(group="fixed", layer="deploy", service="Compute Engine VM", sku_tier="e2-standard-4", vcpu=4, ram_gb=16, qty=E(1, 1, 2, 3)),
        dict(group="fixed", layer="data", service="Cloud SQL", sku_tier="PostgreSQL, HA", vcpu=4, ram_gb=16, qty=E(1, 1, 1, 1)),
        dict(group="fixed", layer="tools", service="MCP Server (Cloud Run)", sku_tier="1 vCPU 2 GiB", vcpu=1, ram_gb=2, qty=E(1, 1, 1, 2)),
        dict(group="fixed", layer="model", service="Vertex AI Gemini (LLM)", sku_tier="Gemini 2.5 Flash", qty=E(1, 1, 1, 1), usage=E(5, 5, 10, 200)),
        dict(group="fixed", layer="memory", service="Memorystore for Redis", sku_tier="Standard tier", qty=E(1, 1, 1, 5)),
        dict(group="fixed", layer="model", service="Vertex AI Gemini Output (LLM)", sku_tier="Gemini 2.5 Flash", qty=E(1, 1, 1, 1), usage=E(2, 2, 4, 80)),
        dict(group="nfr", layer="sec_perimeter", service="Cloud Armor", sku_tier="WAF policy", qty=E(1, 1, 1, 1)),
        dict(group="nfr", layer="sec_data", service="Secret Manager", sku_tier="Active versions", qty=E(5, 5, 5, 10)),
        dict(group="nfr", layer="ops", service="Cloud Logging", sku_tier="Standard", qty=E(1, 1, 1, 1), usage=E(10, 10, 20, 300)),
        dict(group="nfr", layer="sec_identity", service="Cloud IAM & Workload Identity Federation", sku_tier="", qty=E(1, 1, 1, 1)),
    ]
    req = BomRequest(use_case="Customer support agent for order status", provider="anthropic", model="x", api_key="x")
    state = {"req": req, "bom": LlmBom(components=comps)}
    state.update(graph.fetch_prices(state))
    state.update(graph.calculate(state))
    return state["rows"], state["totals"]


def money(v):
    return "" if v is None else f"{v:,.2f}"


def build():
    pdf = Doc(format="A4")
    pdf.set_margins(16, 14, 16)
    pdf.set_auto_page_break(True, 16)
    pdf.add_font("body", "", str(FONTS / "arial.ttf"))
    pdf.add_font("body", "B", str(FONTS / "arialbd.ttf"))
    pdf.add_font("body", "I", str(FONTS / "ariali.ttf"))
    pdf.add_font("mono", "", str(FONTS / "consola.ttf"))
    pdf.set_title("GCP Enterprise BOM Agent - Pricing strategy, calculations and catalogue")

    C = catalog.CATALOG
    n_fixed = sum(1 for s in C.values() if s["group"] == "fixed")
    n_free = sum(1 for s in C.values() if s.get("free"))
    no_price = [n for n, s in C.items() if s["mode"] == "usage" and s["plabel"] not in catalog.USAGE_UNITS]
    modes = {m: sum(1 for s in C.values() if s["mode"] == m and not s.get("free")) for m in ("hour", "shape", "month", "usage")}

    # ------------------------------------------------------------ cover
    pdf.add_page()
    pdf.set_fill_color(*BLUE)
    pdf.rect(0, 0, pdf.w, 4, style="F")
    pdf.ln(30)
    pdf.set_font("body", "B", 26)
    pdf.set_text_color(*DARK)
    pdf.multi_cell(0, 12, "GCP Enterprise BOM Agent")
    pdf.set_font("body", "", 16)
    pdf.set_text_color(*BLUE)
    pdf.multi_cell(0, 9, "Pricing strategy, cost calculations and service catalogue")
    pdf.ln(6)
    pdf.set_font("body", "", 11)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(0, 6, "How the agent turns a use case into a priced bill of materials: what happens at each step, "
                         "which numbers come from the LLM and which from Google Cloud, every formula the code applies, "
                         "the assumptions behind them, and how the Pipeline tab differs from the BOM tab.")
    pdf.ln(10)
    pdf.note(f"**At a glance**\n"
             f"• Catalogue: {len(C)} GCP services ({n_fixed} functional / {len(C) - n_fixed} non-functional), "
             f"{len(catalog.LAYERS)} architecture layers, 4 environments ({', '.join(ENVS)}).\n"
             f"• Prices: live list prices from the free Cloud Billing Catalog API (USD, on-demand), cached 1 hour; "
             f"labelled static approximations when no live match exists.\n"
             f"• Cost: monthly, per environment, using one of four pricing modes (hour, shape, month, usage) plus "
             f"tier-by-tier costing for tiered SKUs.\n"
             f"• Quantities and usage volumes are estimated by the LLM; prices are never estimated by the LLM.")
    pdf.set_font("body", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.ln(4)
    pdf.multi_cell(0, 5, "Source files analysed: backend/catalog.py, backend/pricing.py, backend/graph.py, backend/prompts.py, "
                         "backend/schemas.py, backend/test_pricing.py, frontend/index.html, KnowledgeBase/*.md.\n"
                         "Catalogue tables and the worked example in this document are generated directly from the code "
                         "(docs/build_pricing_pdf.py).")

    # ------------------------------------------------------------ 1. overview
    pdf.add_page()
    pdf.h1("1. What happens when a BOM is generated")
    pdf.p("The user enters a use case, the non-functional requirements (NFRs), a region (chosen from a dropdown of GCP regions, default asia-south1) "
          "and LLM settings, then clicks **Design & build BOM**. The browser sends "
          "POST /api/bom and the backend runs a six-node LangGraph agent (backend/graph.py):")
    flow(pdf)
    pdf.grid([
        ["Node", "What it does", "Output"],
        ["load_kb", "Extracts four reference sections from the knowledge base: the L2 layer stack, the L3 layer-to-service "
                    "index, the Security & Governance components and the GCP BOM table.", "kb text"],
        ["build_prompt", "System prompt = architect role + KB + the 18 layer ids + the allowed service list (with each "
                         "service's count unit and usage unit) + 13 rules + a JSON example. User prompt = use case + NFRs "
                         "(plus the previous error on a retry).", "system, user"],
        ["call_llm", "Calls the chosen provider (OpenAI-compatible, Azure OpenAI, Anthropic, Gemini) at temperature 0; "
                     "retries without temperature if the model rejects it. Records the stop reason.", "raw answer"],
        ["validate_json", "Strips fences, repairs trailing commas, validates against LlmBom (qty ≥ 0 integers, usage ≥ 0, "
                          "all 4 environments filled), rejects services not in the catalogue, maps aliases to canonical "
                          "names (e.g. 'gke' → Google Kubernetes Engine (cluster)).", "bom or error"],
        ["fetch_prices", "Prices every component via pricing.price_items(); fixes the layer with normalize_layer(); "
                         "attaches group, section, count unit and usage unit.", "rows"],
        ["calculate", "Monthly cost per environment for each row, the formula text, and totals per group / environment.", "totals"],
    ], (26, 128, 24), size=8.3)

    pdf.h2("Division of responsibility: LLM vs code")
    pdf.grid([
        ["Decided by the LLM (an estimate)", "Decided by the code (deterministic)"],
        ["Which catalogue services the solution needs, and their layer", "The list of services that may be used (catalog.py)"],
        ["sku_tier (size / edition / model name), vCPU and RAM per instance", "Which live SKU is matched and its unit price"],
        ["qty per environment (instances / nodes / GB / policies ...)", "Unit conversion between the SKU unit and the cost unit"],
        ["usage per environment (monthly volume in the service's usage unit)", "Tier-by-tier costing, scope and rounding"],
        ["logical component, reason, qty_reason, assumptions, MCP tools", "Monthly cost, formula text, totals"],
    ], (89, 89), size=8.5)
    pdf.note("The LLM never supplies a price. Every dollar figure is either a live Google Cloud list price or a static "
             "approximation from catalog.py, and the row's **source** label says which. Quantities and volumes, "
             "however, are LLM judgement calls and are the biggest source of estimate error.", AMBER)

    # ------------------------------------------------------------ 2. catalogue
    pdf.h1("2. The service catalogue (backend/catalog.py)")
    pdf.p("catalog.py is the single source of truth for what the LLM may choose and how each service is priced. "
          f"It defines **{len(C)} services** ({n_fixed} in group 'fixed', {len(C) - n_fixed} in group 'nfr'), of which "
          f"**{n_free} are free** and the rest are priced from the Cloud Billing Catalog. Every service is a GCP product named in the "
          "knowledge base or needed to run it. Where the Cloud Billing catalogue has no matching SKU, the price comes from the "
          "public GCP list-price page and the row's source says so.")
    pdf.h2("2.1 Fields of a catalogue entry")
    pdf.grid([
        ["Field", "Meaning"],
        ["group", "'fixed' = functional (FR) solution component; 'nfr' = non-functional (security, governance, operations)."],
        ["unit", "Count unit for qty, e.g. cluster, VM, instance, node, GB, security policy, key version."],
        ["mode", "Pricing mode: hour, shape, month or usage (see 2.2). 'free' services are costed at $0."],
        ["static", "Approximate USD list price used ONLY when no live SKU matches (None = no reliable list price)."],
        ["catalog", "Cloud Billing service display-name candidates, e.g. ['Cloud Run Functions', 'Cloud Functions']."],
        ["req / pref / excl", "SKU description tokens that are required / ranked higher / excluded during matching."],
        ["plabel", "Usage price basis, e.g. 'per 1M input tokens'; must be a key of USAGE_UNITS to be costed."],
        ["aliases", "Alternative names the LLM may write; mapped to the canonical name by canonical_service()."],
        ["shape, static_cpu, static_ram", "Shape-mode services only: SKU family preference and static $/vCPU-hr, $/GiB-hr."],
    ], (38, 140), size=8.5)

    pdf.h2("2.2 The four pricing modes")
    pdf.grid([
        ["Mode", "Services", "Monthly cost per environment", "Examples"],
        ["hour", str(modes["hour"]), "qty × hours/month × $ per unit-hour", "GKE cluster fee, Spanner node, Memorystore GB, Apigee, Cloud NAT"],
        ["shape", str(modes["shape"]), "qty × hours/month × (vCPU × $/vCPU-hr + GiB × $/GiB-hr)", "Compute Engine, Cloud Run, MCP Server, Cloud SQL, AlloyDB, gVisor sandbox"],
        ["month", str(modes["month"]), "qty × $ per unit-month", "Cloud Armor policy, KMS key version, Secret Manager, Cloud DNS zone, Scheduler job"],
        ["usage", str(modes["usage"]), "usage volume × $ per usage unit (only where qty > 0)", "Gemini tokens, BigQuery TiB, Pub/Sub, Cloud Storage, Logging"],
        ["free", str(n_free), "$0", "IAM / WIF, VPC-SC, Model Registry, Firebase Cloud Messaging, Billing"],
    ], (16, 17, 68, 77), size=8.3)

    pdf.h2("2.3 Usage units (USAGE_UNITS)")
    pdf.p("For usage-mode services the LLM must estimate a monthly volume in the unit shown in the prompt. USAGE_UNITS maps "
          "each price basis to a Cloud Billing unit and a scale, so the live price is converted to exactly the unit the "
          "volume is expressed in. A live SKU billed in a different dimension is rejected rather than mis-read.")
    uu = sorted(catalog.USAGE_UNITS.items(), key=lambda kv: kv[0])
    half = (len(uu) + 1) // 2
    rows = [["Price basis", "Billing unit × scale", "Price basis", "Billing unit × scale"]]
    for i in range(half):
        a = uu[i]
        b = uu[i + half] if i + half < len(uu) else ("", ("", ""))
        fmt = lambda u: f"{u[0]} × {u[1]:,.6g}" if u[0] else ""  # noqa: E731
        rows.append([a[0], fmt(a[1]), b[0], fmt(b[1])])
    pdf.grid(rows, (46, 43, 46, 43), size=8)

    pdf.h2("2.4 Architecture layers")
    pdf.p("Each component is placed in one of 18 layers from the IBM multi-agent reference architecture (GCP view). FR layers "
          "take 'fixed' services; NFR layers take 'nfr' services. If the LLM gives an invalid layer, or one of the wrong "
          "kind, normalize_layer() falls back to the service's DEFAULT_LAYER (else 'deploy' for FR, 'ops' for NFR).")
    pdf.grid([["Kind", "Section", "Layer id", "Layer name"]] +
             [[l["kind"].upper(), l["section"], l["id"], l["name"]] for l in catalog.LAYERS], (14, 46, 32, 86), size=8)
    pdf.p("The complete per-service catalogue (mode, units, static fallback price, Cloud Billing service names) is in "
          "**Appendix A**.", 9.5)

    # ------------------------------------------------------------ 3. pricing strategy
    pdf.h1("3. Pricing strategy (backend/pricing.py)")
    pdf.p("The strategy is **live list price first, labelled approximation second, never a silent guess**. For every "
          "component price_items() walks this decision chain, and the first matching rule sets the price and its source label:")
    pdf.grid([
        ["#", "Condition", "Price used", "Source label shown"],
        ["1", "Service is marked free in the catalogue", "$0", "free"],
        ["2", "GCP_PRICING_API_KEY is not set", "static from catalog.py", "static (approx; set GCP_PRICING_API_KEY for live prices)"],
        ["3", "Catalog API call failed (bad key, quota, network)", "static", "static (approx; catalog error: <ErrorType>)"],
        ["4", "A live SKU matched with score ≥ 1", "live list price", "gcp-catalog"],
        ["4b", "Live SKU matched, but weakly (score 0 or wrong model version)", "live list price", "gcp-catalog (low match - verify)"],
        ["4c", "Price came from the Pricing API (v1beta) fallback", "live list price", "... + pricing API"],
        ["5", "No SKU matched", "static", "static (approx; no catalog match)"],
        ["6", "No list price exists (static = None)", "not costed", "safety path only; no shipped service uses it"],
    ], (8, 64, 30, 76), size=8.2)

    pdf.h2("3.1 Fetching the catalogue")
    pdf.bullets([
        "GET https://cloudbilling.googleapis.com/v1/services lists all billable GCP services (paged, 5,000 per page).",
        "The service is found by the catalogue's display-name candidates: an exact (case-insensitive) match first, then a substring match.",
        "GET /v1/{service}/skus?currencyCode=USD downloads all SKUs of that service (up to 40 pages).",
        "Services, SKUs and Pricing-API answers are cached in memory for **1 hour** (CACHE_TTL = 3600 s). Before pricing, "
        "the distinct services of the request are downloaded in parallel (8 threads).",
    ])

    pdf.h2("3.2 Matching a SKU (_best)")
    pdf.p("A GCP service has hundreds of SKUs. _best() keeps only plausible ones and ranks them:")
    pdf.bullets([
        "**On-demand only**: category.usageType must be OnDemand.",
        "**Region**: the SKU's serviceRegions must contain the requested region or 'global'.",
        "**Excluded**: descriptions containing commit, preemptible, spot, licens(e), reserv(ed), sole tenancy, windows, GPU, TPU or premium image.",
        "**Required tokens** (req) must all be present, e.g. Cloud NAT needs 'nat', Load Balancing needs 'forwarding' + 'rule'; "
        "**excluded tokens** (excl) rule a SKU out, e.g. Gemini excludes caching, batch, image, audio, video, tuning, long-context SKUs.",
        "**Score** = number of wanted words found in the SKU description, resource group or resource family. Wanted words = the "
        "catalogue's pref tokens + the words of the LLM's sku_tier (+ shape preferences such as 'min instance' for Cloud Run, "
        "'postgresql' for Cloud SQL, and 'regional' if the tier says HA, else 'zonal'). Words of 4+ letters also match as a prefix.",
        "A SKU that shares no wanted word and has no required/kind token is treated as unrelated and skipped: **no price beats a wrong price**.",
        "Ranking: higher score → exact region beats 'global' → shorter description. The first ranked SKU with a usable, "
        "convertible, non-zero price wins.",
        "**Model versions** (usage mode): digits in sku_tier such as '2.5' in 'Gemini 2.5 Flash' must appear in the SKU "
        "description. If no SKU has that version a sibling SKU may be used, but it is flagged 'low match - verify'.",
    ], 9.5)

    pdf.h2("3.3 Reading the price of a SKU (_rate)")
    pdf.bullets([
        "A SKU can carry several pricingInfo entries; the newest one whose effectiveTime is not in the future is used.",
        "Its tieredRates become a ladder [(startUsageAmount, unit price)]. The price shown is the **first non-zero tier**; "
        "a zero-price first tier (free allowance) is never taken as the price.",
        "aggregationInfo sets the tier scope (per billing account or per project) and interval (monthly or daily).",
        "If the catalog entry has no usable price, up to 3 candidate SKUs are looked up in the Pricing API "
        "(v1beta /skus/{id}/price); listPrice is divided by unitQuantity. If that API is unavailable the row falls back to static.",
    ], 9.5)

    pdf.h2("3.4 Unit conversion (_dim / _factor)")
    pdf.p("Billing units such as 'h', 'GiBy.h', 'GiBy.mo', 'GiBy', 'MiBy', 's' or 'count' are parsed into a dimension and a "
          "size in bytes and seconds. The conversion factor = (size of the wanted unit) ÷ (size of the SKU's unit), and is "
          "allowed only when the dimensions match (or match via the SKU's baseUnit). Examples (from test_pricing.py):")
    pdf.grid([
        ["SKU unit", "Wanted cost unit", "Factor", "Why"],
        ["GiBy.mo", "GiBy.h", "1/730", "a month is 730 h in the catalogue"],
        ["GiBy.s", "GiBy.h", "3,600", "Cloud Run memory billed per GiB-second"],
        ["MiBy.h", "GiBy.h", "1,024", "MiB → GiB"],
        ["count", "1M tokens", "1,000,000", "Gemini priced per token, costed per 1M tokens"],
        ["GiBy.h", "h", "rejected", "a per-GiB-hour price is never read as a per-hour price"],
        ["GiBy.mo", "By (egress)", "rejected", "storage is not egress"],
    ], (26, 34, 24, 94), size=8.5)
    pdf.p("Shape mode matches two SKUs, one CPU SKU (per vCPU-hour, any of core/cpu/vcpu, not ram/memory) and one RAM SKU "
          "(per GiB-hour), and combines them: $/instance-hr = vCPU × CPU price + GiB × RAM price. If vCPU or RAM is "
          "missing, the code assumes 1 vCPU and 2 GiB (Cloud Run) or 4 GiB per vCPU (others).", 9.5)

    pdf.h2("3.5 Static fallback prices")
    pdf.p("Each catalogue entry carries an approximate USD list price (Appendix A). It is used only when live pricing is "
          "unavailable, and the row is always labelled 'static (approx; reason)' and shown in amber in the Cost tab. "
          "Static prices are generic: they do not vary by region, by model (e.g. Gemini uses $1.25 per 1M input tokens "
          "whatever model is named), or by edition (e.g. Cloud SQL HA and zonal share the same static vCPU/RAM rates).", 9.5)

    # ------------------------------------------------------------ 4. calculations
    pdf.h1("4. Cost calculations (graph.calculate)")
    pdf.p("H = 730 hours per month (fixed in graph.py as HOURS_PER_MONTH; not a user input). For every row and environment e in {DEV, SIT, UAT, PROD}:")
    pdf.code("hour   : monthly[e] = qty[e] × H × unit_hr\n"
             "shape  : monthly[e] = qty[e] × H × (vCPU × cpu_hr + RAM_GiB × ram_hr)\n"
             "month  : monthly[e] = qty[e] × unit_month\n"
             "free   : monthly[e] = 0\n"
             "usage  : monthly[e] = usage[e] × usage_price      if qty[e] > 0, else 0\n"
             "no list price: monthly = None  (cells left empty, left out of every total; safety path)\n\n"
             "row total      = Σ_e monthly[e]                      (rounded to cents)\n"
             "group total[e] = Σ_rows monthly[e]   for group 'fixed' and 'nfr'\n"
             "grand total    = fixed ALL + nfr ALL")

    pdf.h2("4.1 Tiered SKUs (pricing.tiered_monthly)")
    pdf.p("When a live SKU has more than one tier, or its first tier starts above 0, the row is not costed at a flat rate. "
          "The amount is first expressed in the SKU's own billing unit (unit-hours for hour/shape, unit-months for month, "
          "usage volume for usage), then charged **range by range** (progressive tiers):")
    pdf.code("cost(amount) = Σ_i  (min(amount, start[i+1]) − start[i]) × price[i]      for every tier i with start[i] < amount")
    pdf.bullets([
        "**Account scope** (most SKUs): one ladder is shared by all four environments (one billing account). The ladder is applied to "
        "the summed amount and the cost is split between environments in proportion to their usage.",
        "**Project scope**: each environment is assumed to be its own GCP project, so each gets its own ladder and its own free allowance.",
        "**Daily interval**: the ladder resets each day, so the monthly amount is divided by 730/24 = 30.42 days, laddered, and multiplied back.",
        "The displayed price is the first paid tier with '(tiered)' appended; the formula text lists the whole ladder.",
    ], 9.5)
    # tiered examples computed by the code
    cdn = {"tiered": [{"tiers": [(0, 0.08), (10240, 0.06), (153600, 0.04)], "f": 1.0, "scope": "account", "days": 1.0}]}
    cdn_cost = pricing.tiered_monthly(cdn, {"DEV": 200, "SIT": 0, "UAT": 0, "PROD": 19800})
    logs = {"tiered": [{"tiers": [(0, 0.0), (50, 0.50)], "f": 1.0, "scope": "project", "days": 1.0}]}
    log_cost = pricing.tiered_monthly(logs, {"DEV": 10, "SIT": 30, "UAT": 60, "PROD": 200})
    pdf.grid([
        ["Example (ladder)", "Input", "Result per environment", "Total"],
        ["Cloud CDN egress, account scope: 0+ @ $0.08, 10,240+ @ $0.06, 153,600+ @ $0.04 per GB",
         "DEV 200 GB, PROD 19,800 GB (shared ladder: 20,000 GB)",
         ", ".join(f"{e} {v:,.2f}" for e, v in cdn_cost.items()),
         f"{sum(cdn_cost.values()):,.2f}  (flat $0.08 would give {20000 * 0.08:,.2f})"],
        ["Cloud Logging, project scope: first 50 GiB free, then $0.50 per GiB",
         "DEV 10, SIT 30, UAT 60, PROD 200 GiB",
         ", ".join(f"{e} {v:,.2f}" for e, v in log_cost.items()),
         f"{sum(log_cost.values()):,.2f}"],
    ], (58, 42, 44, 34), size=8)

    pdf.h2("4.2 Formula text")
    pdf.p("Each row gets a human-readable formula built from the same numbers, shown in the Cost tab and the CSV, e.g.:")
    pdf.code("7 VM(s) x 730 h x $0.2060/VM-hr = $1,052.66\n"
             "220.00 1M input tokens x $1.25 = $275.00\n"
             f"20,000.00 GB egress, tiered: 0+ @ $0.08, 10,240+ @ $0.06 ... per GB egress (per billing account per month) = ${sum(cdn_cost.values()):,.2f}\n"
             "(empty)")

    # ------------------------------------------------------------ 5. worked example
    pdf.h1("5. Worked example (computed by the code)")
    pdf.p("The table below is produced by running a sample LLM answer through the real fetch_prices() and calculate() "
          "nodes with no API key, so every row uses the **static** fallback price. With GCP_PRICING_API_KEY set the same "
          "rows would use live, region-specific SKU prices instead. Hours per month = 730 (fixed).")
    ex_rows, ex_tot = worked_example()
    tab = [["Service (group)", "qty D/S/U/P", "Price", "Formula", "Monthly $"]]
    for r in ex_rows:
        tab.append([f"{r['service']} ({r['group']})", "/".join(str(r["qty"][e]) for e in ENVS), r["price_text"],
                    r["formula"], money(r["monthly_total"])])
    pdf.grid(tab, (40, 18, 36, 64, 20), size=7.6)
    pdf.grid([["Totals", *ENVS, "ALL"],
              ["Functional (fixed)", *[f"{ex_tot['fixed'][e]:,.2f}" for e in ENVS], f"{ex_tot['fixed']['ALL']:,.2f}"],
              ["Non-functional (nfr)", *[f"{ex_tot['nfr'][e]:,.2f}" for e in ENVS], f"{ex_tot['nfr']['ALL']:,.2f}"],
              ["Total monthly", "", "", "", "", f"{ex_tot['ALL']:,.2f}"]],
             (48, 26, 26, 26, 26, 26), size=8.3)
    sql = next(r for r in ex_rows if r["service"] == "Cloud SQL")
    gem = next(r for r in ex_rows if r["service"].startswith("Vertex AI Gemini"))
    pdf.p(f"Reading two rows: **Cloud SQL** is shape mode, 4 vCPU × $0.0413 + 16 GiB × $0.007 = $0.2772 per instance-hour; "
          f"× 730 h = {sql['monthly']['DEV']:,.2f} per environment; × 4 environments = {sql['monthly_total']:,.2f}. "
          f"**Gemini** is usage mode: the LLM estimated 5 + 5 + 10 + 200 = 220 million input tokens a month; "
          f"220 × $1.25 = {gem['monthly_total']:,.2f}. Output tokens are a separate row (Vertex AI Gemini Output) at their own, higher price.", 9.5)

    # ------------------------------------------------------------ 6. assumptions
    pdf.h1("6. Assumptions built into the pricing")
    pdf.h2("6.1 Assumptions made by the code")
    pdf.bullets([
        "**Always-on**: hour and shape resources run the full 730 hours a month (24 × 365 / 12), a constant in graph.py. No autoscaling, "
        "scale-to-zero or office-hours schedule is modelled.",
        "**List price, on-demand, USD**: no committed-use or sustained-use discounts, spot/preemptible, negotiated or "
        "marketplace pricing, taxes, support plans or currency conversion.",
        "**One region** for the whole BOM (the region chosen in the dropdown); no multi-region or cross-region replication cost.",
        "**Four environments**, DEV, SIT, UAT and PROD, each treated as a separate GCP project under one billing account "
        "(this matters for project- vs account-scoped tiers).",
        "**Free allowances** are honoured only when they appear as zero-price tiers of the matched SKU; GCP's general "
        "free tier and free trial credits are not applied.",
        "**Compute / database rows price vCPU and RAM only.** Database disk is a separate 'Cloud SQL Storage' row "
        "(per GB-month, Regional SKU for HA); persistent disk, backups, licences, network egress and inter-zone traffic "
        "are not included unless the LLM adds a row for them (egress is listed under Exclusions).",
        "**Cloud SQL / AlloyDB**: an 'HA' sku_tier selects regional (HA) SKUs live; otherwise zonal. The static fallback does not distinguish HA.",
        "**Defaults** when vCPU/RAM are missing: 1 vCPU; 2 GiB (Cloud Run) or 4 GiB per vCPU (others).",
        "**Memorystore** qty is GB of capacity, priced per GiB-hour.",
        "**Usage rows** are costed only in environments where qty > 0; the volume, not the qty, drives cost.",
        "**One price per usage service**: Gemini input and output tokens are two rows ('Vertex AI Gemini (LLM)' and "
        "'Vertex AI Gemini Output (LLM)'), with embeddings as a third; caching and grounding are not priced. Pub/Sub is per TiB "
        "of throughput; Load Balancing per forwarding rule (not data processed); Agent Engine per vCPU-hour.",
        "**One-time build volume**: a usage row may carry 'build_usage' (e.g. the initial document OCR or embedding load). It is "
        "priced once with the same SKU and tiers, shown in a separate 'One-time build' column, and is NOT in the monthly total.",
        "**Exclusions** are listed by the LLM (egress, support plan, discounts, people effort...) and shown in their own card.",
        "**GCP-only catalogue**: every service is a GCP product. Prices come from the Cloud Billing catalogue first; where no SKU "
        "matches, from the public GCP list-price page (source labelled \"web list price\"). The catalogue is use-case independent: "
        "every GCP product the knowledge base names (Looker, Model Garden, AutoML, BigQuery ML, Training Job, Gen AI Evaluation, Code "
        "Execution Sandbox, Distributed Cloud, Gemini Code Assist ...) is offered to the LLM and priced the same way in any region. "
        "Where the SKU is per model or per edition (Model Garden, AutoML, Looker) the sku_tier must name it; a name with no SKU leaves the price cells empty rather than using another model's price.",
        "**Prices are cached for 1 hour** in memory and the newest price already in effect is used.",
    ], 9.3)
    pdf.h2("6.2 Assumptions made by the LLM (per run)")
    pdf.bullets([
        "Which services are needed, their tier/size and their per-environment quantities (non-production normally smaller, "
        "PROD with redundancy where the NFRs ask for it).",
        "Monthly usage volumes derived from users, traffic, peak and retention in the use case and NFRs; the basis of each "
        "estimate is returned in the 'assumptions' list (e.g. 1 lakh chats/day × 4K tokens = 12,000M tokens/month).",
        "These are shown in the Assumptions card and in the CSV, and should be reviewed before the numbers are used. "
        "Temperature 0 makes the answer as repeatable as the provider allows, but different models give different BOMs.",
    ], 9.3)

    # ------------------------------------------------------------ 7. pipeline vs BOM
    pdf.h1("7. Pipeline tab vs BOM tab (and BOQ / Cost)")
    pdf.p("All four result tabs in frontend/index.html render the **same list of rows** returned by /api/bom, in the same "
          "order (reference-architecture layer order: FR layers first, then security, governance, operations). They differ "
          "only in which fields they show, i.e. which question they answer:")
    pdf.grid([
        ["Tab", "Question it answers", "Columns", "Data source of each column"],
        ["Pipeline", "WHAT logical capabilities does the solution need, and what is each for in THIS use case?",
         "Layer · Logical component · Purpose of the layer · Purpose of the component",
         "Layer purpose: LLM 'layer_purposes' (use-case specific; falls back to the generic text in catalog.py LAYERS if the LLM omits a layer). "
         "Logical component: LLM 'logical'. Component purpose: LLM 'purpose' (falls back to 'reason')."],
        ["BOM", "WHICH GCP service realises each logical component, and why?",
         "Layer · Logical component · GCP component · Justification",
         "Canonical service name; LLM reason. SKU / tier, vCPU / RAM and region are shown in BOQ and Cost, not repeated here."],
        ["BOQ", "HOW MANY of each, per environment, and how much usage?",
         "GCP component · SKU · DEV · SIT · UAT · PROD · Total instances · Monthly volume · Justification",
         "LLM qty, usage, qty_reason; totals computed in calculate()."],
        ["Cost", "HOW MUCH per month?",
         "BOM component · Total instances · Price + source · Formula · Monthly ($); group & grand totals",
         "pricing.py price and source; calculate() formula, row and group totals."],
    ], (17, 40, 55, 66), size=8)
    pdf.h2("Key differences between Pipeline and BOM")
    pdf.bullets([
        "**Abstraction level**: Pipeline is the logical architecture (vendor-neutral capabilities such as 'Short-Term Session "
        "Memory' or 'Generative AI Model', from the KB's Logical → Physical mapping). BOM is the physical bill of materials: "
        "concrete GCP products with size/edition and region.",
        "**Content**: Pipeline explains the *purpose* of each layer and of each component for this use case (both written "
        "by the LLM from the use case). BOM names the physical GCP service and why it was chosen. Neither shows SKU/tier, "
        "region, quantity or price; those are in BOQ and Cost.",
        "**Row count**: both show exactly one row per BOM component (the tab badges show the same number). The Pipeline is "
        "not de-duplicated, so one logical component realised by several services, or by the same service at different "
        "sizes (separate rows per sku_tier), appears more than once.",
        "**Neither tab shows cost**: the money is only in the Cost tab, quantities only in BOQ. Pipeline → BOM → BOQ → Cost "
        "is a progressive drill-down of the same data, and the CSV export contains all of their columns in one sheet.",
    ], 9.5)

    # ------------------------------------------------------------ 8. limitations
    pdf.h1("8. Limitations and points to verify")
    pdf.bullets([
        "Rows labelled 'static (approx ...)' or 'low match - verify' should be checked against the GCP pricing calculator; "
        "hover over the source in the Cost tab to see the matched SKU description.",
        "Usage volumes are the largest uncertainty; check the assumption that backs each volume. Gemini input and output tokens are "
        "separate rows, so check that both volumes are present.",
        "Compute and database rows exclude storage, disks and egress, so add rows or a contingency for them.",
        "Web list prices are the published rate, not a negotiated one; check them against the calculator. CCAI and SCC are priced from the public pages where the catalogue has no match.",
        "There is no discount modelling (CUD/SUD/EDP); actual invoices for long-running PROD workloads are usually lower than list.",
        "README.md section 7.2 describes an earlier UI (FR/NFR tabs and a layer sidebar); the current page uses the "
        "Pipeline / BOM / BOQ / Cost tabs described in section 7 of this document.",
    ], 9.5)

    # ------------------------------------------------------------ appendix
    pdf.h1("Appendix A. Full service catalogue")
    pdf.p("Generated from catalog.CATALOG. 'Static' is the fallback price used only when no live SKU matches; "
          "'Billing service' is the Cloud Billing display name searched for live prices ('-' = static/free only).", 9)
    for grp, title in (("fixed", "A.1 Functional (fixed / platform) services"), ("nfr", "A.2 Non-functional services")):
        pdf.h2(title)
        rows = [["Service", "Mode", "Count unit", "Static fallback price", "Billing service"]]
        for n, s in C.items():
            if s["group"] != grp:
                continue
            if s.get("free"):
                price, mode = "Free", "free"
            elif s["mode"] == "shape":
                price, mode = f"${s['static_cpu']}/vCPU-hr + ${s['static_ram']}/GiB-hr", "shape"
            elif s["mode"] == "hour":
                price, mode = f"${s['static']:g} / {s['unit']}-hr", "hour"
            elif s["mode"] == "month":
                price, mode = f"${s['static']:g} / {s['unit']}-month", "month"
            elif s["static"] is None or s["plabel"] not in catalog.USAGE_UNITS:
                price, mode = f"no list price ({s['plabel']})", "usage"
            else:
                price, mode = f"${s['static']:g} {s['plabel']}", "usage"
            rows.append([n, mode, s["unit"], price, s["catalog"][0] if s["catalog"] else "-"])
        pdf.grid(rows, (50, 13, 25, 52, 38), size=7.6)

    pdf.output(str(OUT))
    print(f"wrote {OUT} ({pdf.page_no()} pages)")


if __name__ == "__main__":
    build()
