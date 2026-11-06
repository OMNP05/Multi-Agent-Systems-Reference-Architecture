"""LangGraph agent: load_kb -> build_prompt -> call_llm -> validate -> fetch_prices -> calculate."""
import json
import re
from typing import Any, Dict, List, Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

import catalog
import prompts
import pricing
from schemas import ENVS, BomRequest, LlmBom

MAX_ATTEMPTS = 3  # first try + two retries


class State(TypedDict, total=False):
    req: BomRequest
    kb: str
    system: str
    user: str
    raw: str
    stop: Optional[str]
    attempts: int
    error: Optional[str]
    bom: Optional[LlmBom]
    rows: List[Dict[str, Any]]
    totals: Dict[str, Any]
    failed: bool


def make_llm(req: BomRequest, use_temp: bool = True):
    """Build the LangChain chat model for the provider chosen in the dropdown."""
    t = {"temperature": 0} if use_temp else {}
    if req.provider == "openai_compatible":
        from langchain_openai import ChatOpenAI
        kw = {"base_url": req.endpoint} if req.endpoint else {}
        return ChatOpenAI(model=req.model, api_key=req.api_key, timeout=240, **t, **kw)
    if req.provider == "azure_openai":
        from langchain_openai import AzureChatOpenAI
        if not req.endpoint:
            raise ValueError("Azure OpenAI needs the endpoint URL")
        return AzureChatOpenAI(azure_endpoint=req.endpoint, azure_deployment=req.model, api_key=req.api_key,
                               api_version="2024-06-01", timeout=240, **t)
    if req.provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        kw = {"base_url": req.endpoint} if req.endpoint else {}
        return ChatAnthropic(model=req.model, api_key=req.api_key, timeout=240, max_tokens=16000, **t, **kw)
    if req.provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=req.model, google_api_key=req.api_key, **t)
    raise ValueError(f"Unknown provider {req.provider}")


def _text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p if isinstance(p, str) else p.get("text", "") for p in content)
    return str(content)


def _extract_json(raw: str) -> dict:
    s = raw.strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s, flags=re.S)
    i, j = s.find("{"), s.rfind("}")
    if i < 0 or j < 0:
        raise ValueError("no JSON object found in the answer")
    body = s[i : j + 1]
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        try:  # common LLM slip: trailing commas
            return json.loads(re.sub(r",\s*([}\]])", r"\1", body))
        except json.JSONDecodeError:
            pass
        near = body[max(0, e.pos - 80) : e.pos + 80]
        raise ValueError(f"invalid JSON ({e.msg}) at char {e.pos} of {len(body)}, near: {near!r}")


# ---- nodes ---------------------------------------------------------------
def load_kb(state: State) -> State:
    kb = prompts.load_kb()
    if not kb:
        raise RuntimeError("Knowledge base not found in the KnowledgeBase folder")
    return {"kb": kb, "attempts": 0, "error": None}


def build_prompt(state: State) -> State:
    system, user = prompts.build_prompt(state["req"].use_case, state["req"].nfr, state["req"].region, state["kb"], state.get("error"))
    return {"system": system, "user": user}


def call_llm(state: State) -> State:
    messages = [SystemMessage(content=state["system"]), HumanMessage(content=state["user"])]
    try:
        msg = make_llm(state["req"]).invoke(messages)
    except Exception as e:
        # Some models (e.g. newer Claude/OpenAI reasoning models) reject a non-default temperature.
        if "temperature" not in str(e).lower():
            raise
        msg = make_llm(state["req"], use_temp=False).invoke(messages)
    meta = getattr(msg, "response_metadata", None) or {}
    stop = meta.get("stop_reason") or meta.get("finish_reason")
    return {"raw": _text(msg.content), "stop": stop, "attempts": state.get("attempts", 0) + 1}


def validate_json(state: State) -> State:
    try:
        bom = LlmBom.model_validate(_extract_json(state["raw"]))
        bad = [c.service for c in bom.components if not prompts.canonical_service(c.service)]
        if bad:
            raise ValueError(f"services not in the allowed list: {bad}")
        for c in bom.components:
            c.service = prompts.canonical_service(c.service)
        return {"bom": bom, "error": None, "failed": False}
    except Exception as e:
        msg = str(e)
        if state.get("stop") in ("max_tokens", "length"):
            msg = "your answer was cut off because it was too long; make it shorter (fewer words per field). " + msg
        return {"bom": None, "error": msg[:700], "failed": state.get("attempts", 0) >= MAX_ATTEMPTS}


def after_validate(state: State) -> str:
    if state.get("bom"):
        return "fetch_prices"
    return "end" if state.get("failed") else "build_prompt"


def fetch_prices(state: State) -> State:
    region = state["req"].region
    items = []
    for c in state["bom"].components:
        items.append({"service": c.service, "sku_tier": c.sku_tier, "region": region,
                      "vcpu": c.vcpu, "ram_gb": c.ram_gb})
    prices = pricing.price_items(items)  # live from the Cloud Billing Catalog API when a key is set
    rows = []
    for c, p in zip(state["bom"].components, prices):
        spec = catalog.CATALOG[c.service]
        lay = catalog.LAYER_BY_ID[catalog.normalize_layer(c.layer, c.service)]
        rows.append({
            "group": spec["group"], "layer_id": lay["id"], "layer": lay["name"], "section": lay["section"],
            "service": c.service, "sku_tier": c.sku_tier,
            "region": region, "unit": spec["unit"], "vcpu": c.vcpu, "ram_gb": c.ram_gb, "qty": c.qty,
            "mode": p["mode"], "price_text": p["price_text"], "source": p["source"], "sku_desc": p["sku_desc"],
            "_p": p,
        })
    return {"rows": rows}


def calculate(state: State) -> State:
    hours = state["req"].hours_per_month
    tot = {g: {e: 0.0 for e in ENVS} for g in ("fixed", "nfr")}
    for r in state["rows"]:
        p = r.pop("_p")
        monthly = None  # None = usage-based, not computable without volumes
        if p["mode"] in ("hour", "shape"):
            monthly = {e: round(r["qty"][e] * hours * p["unit_hr"], 2) for e in ENVS}
        elif p["mode"] in ("month", "free"):
            monthly = {e: round(r["qty"][e] * p.get("unit_month", 0.0), 2) for e in ENVS}
        r["monthly"] = monthly
        r["monthly_total"] = round(sum(monthly.values()), 2) if monthly else None
        if monthly:
            for e in ENVS:
                tot[r["group"]][e] += monthly[e]
    totals = {}
    for g in tot:
        totals[g] = {e: round(v, 2) for e, v in tot[g].items()}
        totals[g]["ALL"] = round(sum(tot[g].values()), 2)
    totals["ALL"] = round(totals["fixed"]["ALL"] + totals["nfr"]["ALL"], 2)
    return {"totals": totals}


def build_graph():
    g = StateGraph(State)
    g.add_node("load_kb", load_kb)
    g.add_node("build_prompt", build_prompt)
    g.add_node("call_llm", call_llm)
    g.add_node("validate_json", validate_json)
    g.add_node("fetch_prices", fetch_prices)
    g.add_node("calculate", calculate)
    g.add_edge(START, "load_kb")
    g.add_edge("load_kb", "build_prompt")
    g.add_edge("build_prompt", "call_llm")
    g.add_edge("call_llm", "validate_json")
    g.add_conditional_edges("validate_json", after_validate,
                            {"fetch_prices": "fetch_prices", "build_prompt": "build_prompt", "end": END})
    g.add_edge("fetch_prices", "calculate")
    g.add_edge("calculate", END)
    return g.compile()


GRAPH = build_graph()


def run_agent(req: BomRequest) -> dict:
    out = GRAPH.invoke({"req": req})
    if not out.get("bom"):
        raise ValueError(f"The LLM did not return a valid BOM after {out.get('attempts', 0)} attempts: {out.get('error')}")
    return {
        "assumptions": out["bom"].assumptions,
        "mcp_tools": out["bom"].mcp_tools,
        "layers": [{k: l[k] for k in ("id", "name", "section", "kind", "purpose")} for l in catalog.LAYERS],
        "rows": out["rows"],
        "totals": out["totals"],
        "envs": ENVS,
        "hours_per_month": req.hours_per_month,
    }


if __name__ == "__main__":
    # Print the agent graph in the terminal:  python graph.py
    print(GRAPH.get_graph().draw_ascii())
