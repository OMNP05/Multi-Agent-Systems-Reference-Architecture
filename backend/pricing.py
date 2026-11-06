"""Unit prices from the Cloud Billing Catalog API (free), fetched when a request is made.

The catalog is cached in memory for CACHE_TTL seconds so repeated requests stay fast.
If there is no API key, or a service cannot be matched, an approximate static price
is used and the row's source says so - nothing is silently guessed.
"""
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import httpx

from catalog import CATALOG

BASE = "https://cloudbilling.googleapis.com/v1"
CACHE_TTL = 3600  # seconds
HOURS_PER_MONTH_CATALOG = 730.0

_lock = threading.Lock()
_services_cache: tuple = (0.0, [])
_skus_cache: dict = {}

_TIME = {"s": 3600.0, "min": 60.0, "h": 1.0, "d": 1 / 24, "wk": 1 / 168, "mo": 1 / HOURS_PER_MONTH_CATALOG}
_BAD = re.compile(r"commit|preemptible|spot|licens|reserv|sole tenancy|windows|gpu|tpu|premium image")
_CPU, _RAM = ("core", "cpu", "vcpu"), ("ram", "memory")
_SHAPE_PREF = {"compute": (), "cloudrun": ("min", "instance"), "cloudsql": ("postgresql",), "alloydb": ()}


def _tok(text: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if not t.isdigit() and len(t) > 1}


def _get(path: str, key: str, params: Optional[dict] = None) -> dict:
    r = httpx.get(f"{BASE}{path}", params={"key": key, **(params or {})}, timeout=60)
    r.raise_for_status()
    return r.json()


def _services(key: str) -> list:
    global _services_cache
    ts, data = _services_cache
    if data and time.time() - ts < CACHE_TTL:
        return data
    out, token = [], None
    while True:
        d = _get("/services", key, {"pageSize": 5000, **({"pageToken": token} if token else {})})
        out += d.get("services", [])
        token = d.get("nextPageToken")
        if not token:
            break
    with _lock:
        _services_cache = (time.time(), out)
    return out


def _skus(service_name: str, key: str) -> list:
    hit = _skus_cache.get(service_name)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    out, token, pages = [], None, 0
    while pages < 40:
        d = _get(f"/{service_name}/skus", key, {"currencyCode": "USD", "pageSize": 5000, **({"pageToken": token} if token else {})})
        out += d.get("skus", [])
        token = d.get("nextPageToken")
        pages += 1
        if not token:
            break
    with _lock:
        _skus_cache[service_name] = (time.time(), out)
    return out


def _find_service(names: list, key: str):
    svcs = _services(key)
    for n in names:
        for s in svcs:
            if s.get("displayName", "").lower() == n.lower():
                return s
    for n in names:
        for s in svcs:
            if n.lower() in s.get("displayName", "").lower():
                return s
    return None


def _rate(sku: dict):
    """(price, usageUnit, unit description) of the first non-zero pricing tier."""
    try:
        expr = sku["pricingInfo"][0]["pricingExpression"]
        for tier in expr["tieredRates"]:
            up = tier["unitPrice"]
            price = float(up.get("units", 0) or 0) + up.get("nanos", 0) / 1e9
            if price > 0:
                return price, expr.get("usageUnit", ""), expr.get("usageUnitDescription", "")
    except (KeyError, IndexError, ValueError):
        pass
    return None


def _per_hour(price: float, unit: str):
    f = _TIME.get(unit.split(".")[-1]) if unit else None
    return None if f is None else price * f


def _best(skus: list, region: str, *, need_time: bool, req=(), any_kw=(), not_kw=(), want=frozenset()):
    """Best matching on-demand SKU for this region. Returns dict or None."""
    best, best_key = None, None
    for sku in skus:
        if sku.get("category", {}).get("usageType") != "OnDemand":
            continue
        regions = sku.get("serviceRegions", [])
        if region not in regions and "global" not in regions:
            continue
        desc = sku.get("description", "")
        low = desc.lower()
        toks = _tok(desc)
        if _BAD.search(low) or any(r not in toks for r in req):
            continue
        if any_kw and not (toks & set(any_kw)):
            continue
        if toks & set(not_kw):
            continue
        rate = _rate(sku)
        if not rate:
            continue
        price, unit, udesc = rate
        if need_time and _per_hour(price, unit) is None:
            continue
        score = len(want & toks) + (0.5 if region in regions else 0)
        key = (score, -len(desc))
        if best_key is None or key > best_key:
            best_key = key
            best = {"price": price, "unit": unit, "udesc": udesc, "desc": desc, "score": score}
    return best


def _src(m: dict) -> str:
    return "gcp-catalog" if m["score"] >= 1 else "gcp-catalog (low match - verify)"


def _static(item: dict, s: dict, reason: str) -> dict:
    mode = s["mode"]
    src = f"static (approx; {reason})"
    unit = s["unit"]
    if s.get("free"):
        return {"mode": "free", "source": "free", "sku_desc": "", "unit_hr": 0.0, "unit_month": 0.0, "price_text": "Free"}
    if mode == "hour":
        return {"mode": mode, "source": src, "sku_desc": "", "unit_hr": s["static"], "price_text": f"${s['static']:.4f} / {unit}-hr"}
    if mode == "shape":
        v, r = _dims(item, s)
        hr = v * s["static_cpu"] + r * s["static_ram"]
        return {"mode": mode, "source": src, "sku_desc": "", "unit_hr": hr, "price_text": f"${hr:.4f} / {unit}-hr ({v:g} vCPU, {r:g} GiB)"}
    if mode == "month":
        return {"mode": mode, "source": src, "sku_desc": "", "unit_month": s["static"], "price_text": f"${s['static']:.2f} / {unit}-month"}
    basis = s["plabel"] or f"per {unit}"
    if s["static"] is None:
        return {"mode": "usage", "source": "no fixed list price", "sku_desc": "", "usage_price": None, "price_text": basis}
    return {"mode": "usage", "source": src, "sku_desc": "", "usage_price": s["static"], "price_text": f"${s['static']:g} {basis}"}


def _dims(item: dict, s: dict):
    v = item.get("vcpu") or 0
    r = item.get("ram_gb") or 0
    if v <= 0:
        v = 1.0
    if r <= 0:
        r = 2.0 if s.get("shape") == "cloudrun" else v * 4
    return float(v), float(r)


def _live(item: dict, s: dict, key: str) -> Optional[dict]:
    region, unit, mode = item["region"], s["unit"], s["mode"]
    svc = _find_service(s["catalog"], key)
    if not svc:
        return None
    skus = _skus(svc["name"], key)
    want = set(s["pref"]) | _tok(item["sku_tier"])
    if mode == "hour":
        m = _best(skus, region, need_time=True, req=s["req"], want=want)
        if not m:
            return None
        hr = _per_hour(m["price"], m["unit"])
        return {"mode": mode, "source": _src(m), "sku_desc": m["desc"], "unit_hr": hr, "price_text": f"${hr:.4f} / {unit}-hr"}
    if mode == "shape":
        shape = s["shape"]
        want |= set(_SHAPE_PREF.get(shape, ()))
        if shape in ("cloudsql", "alloydb"):
            want |= {"regional"} if "ha" in item["sku_tier"].lower().split() or "ha" in _tok(item["sku_tier"]) else {"zonal"}
        cpu = _best(skus, region, need_time=True, any_kw=_CPU, not_kw=_RAM, want=want)
        ram = _best(skus, region, need_time=True, any_kw=_RAM, want=want)
        if not cpu or not ram:
            return None
        v, r = _dims(item, s)
        hr = v * _per_hour(cpu["price"], cpu["unit"]) + r * _per_hour(ram["price"], ram["unit"])
        m = {"score": min(cpu["score"], ram["score"])}
        return {"mode": mode, "source": _src(m), "sku_desc": f"{cpu['desc']} + {ram['desc']}", "unit_hr": hr,
                "price_text": f"${hr:.4f} / {unit}-hr ({v:g} vCPU, {r:g} GiB)"}
    if mode == "month":
        m = _best(skus, region, need_time=True, req=s["req"], want=want)
        if not m:
            return None
        pm = _per_hour(m["price"], m["unit"]) * HOURS_PER_MONTH_CATALOG
        return {"mode": mode, "source": _src(m), "sku_desc": m["desc"], "unit_month": pm, "price_text": f"${pm:.2f} / {unit}-month"}
    m = _best(skus, region, need_time=False, req=s["req"], want=want)  # usage
    if not m:
        return None
    basis = f"per {m['udesc']}" if m["udesc"] else f"per {m['unit']}"
    return {"mode": "usage", "source": _src(m), "sku_desc": m["desc"], "usage_price": m["price"], "price_text": f"${m['price']:.6g} {basis}"}


def price_items(items: list) -> list:
    """items: dicts with service, sku_tier, region, vcpu, ram_gb. Returns one price dict per item."""
    key = os.environ.get("GCP_PRICING_API_KEY", "").strip()
    errors: dict = {}

    if key:
        # Warm the caches in parallel (one catalog download per distinct GCP service).
        def warm(n):
            try:
                svc = _find_service(CATALOG[n]["catalog"], key)
                if svc:
                    _skus(svc["name"], key)
            except Exception as e:  # bad key / quota / network
                errors[n] = f"{type(e).__name__}"
        try:
            _services(key)
        except Exception as e:
            errors["*"] = f"{type(e).__name__}"
        if "*" not in errors:
            names = sorted({it["service"] for it in items if CATALOG[it["service"]]["catalog"]})
            with ThreadPoolExecutor(max_workers=8) as ex:
                list(ex.map(warm, names))

    out = []
    for it in items:
        s = CATALOG[it["service"]]
        if s.get("free"):
            out.append(_static(it, s, ""))
            continue
        if not key:
            out.append(_static(it, s, "set GCP_PRICING_API_KEY for live prices"))
            continue
        err = errors.get("*") or errors.get(it["service"])
        if err:
            out.append(_static(it, s, f"catalog error: {err}"))
            continue
        try:
            res = _live(it, s, key)
        except Exception as e:
            res = None
            err = type(e).__name__
        out.append(res or _static(it, s, f"no catalog match{' / ' + err if err else ''}"))
    return out
