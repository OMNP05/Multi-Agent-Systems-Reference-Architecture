"""Unit prices from the Cloud Billing Catalog API (free), fetched when a request is made.

The catalog is cached in memory for CACHE_TTL seconds so repeated requests stay fast.
The Pricing API (v1beta /skus/{id}/price) is asked only for a matched SKU whose catalog
entry carries no usable price. Tiered SKUs are costed range by range (see tiered()).
If there is no API key, or a service cannot be matched, an approximate static price
is used and the row's source says so - nothing is silently guessed.
"""
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

from catalog import CATALOG, USAGE_UNITS

load_dotenv(Path(__file__).resolve().parent / ".env")  # backend/.env; real environment variables take precedence

BASE = "https://cloudbilling.googleapis.com/v1"
PRICE_API = "https://cloudbilling.googleapis.com/v1beta"
CACHE_TTL = 3600  # seconds
HOURS_PER_MONTH_CATALOG = 730.0

_lock = threading.Lock()
_services_cache: tuple = (0.0, [])
_skus_cache: dict = {}
_price_cache: dict = {}  # Pricing API answers per SKU id


_TIME = {"s": 3600.0, "min": 60.0, "h": 1.0, "d": 1 / 24, "wk": 1 / 168, "mo": 1 / HOURS_PER_MONTH_CATALOG}  # per hour
_BYTES = {"By": 1, "KiBy": 2 ** 10, "MiBy": 2 ** 20, "GiBy": 2 ** 30, "TiBy": 2 ** 40, "PiBy": 2 ** 50,
          "kBy": 1e3, "MBy": 1e6, "GBy": 1e9, "TBy": 1e12, "PBy": 1e15}
_BAD = re.compile(r"commit|preemptible|spot|licens|reserv|sole tenancy|windows|\bgpus?\b|\btpus?\b|premium image")  # \b: "output" contains "tpu"
_CPU, _RAM = ("core", "cpu", "vcpu"), ("ram", "memory")
_SHAPE_PREF = {"compute": (), "cloudrun": ("min", "instance"), "cloudsql": ("postgresql",), "alloydb": ("instance",)}
_SHAPE_EXCL = {"alloydb": ("lssd", "express")}  # SSD-local and Express are other AlloyDB products


_TIER_NOISE = {"model", "models", "input", "output", "token", "tokens", "maas", "standard", "api", "service", "serverless"}


def _tok(text: str) -> set:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if not t.isdigit() and len(t) > 1}


def _get(path: str, key: str, params: Optional[dict] = None, base: str = BASE) -> dict:
    r = httpx.get(f"{base}{path}", params={"key": key, **(params or {})}, timeout=60)
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


def _money(m: dict) -> float:
    return float(m.get("units") or 0) + float(m.get("nanos") or 0) / 1e9


def _when(info: dict) -> datetime:
    try:
        d = datetime.fromisoformat(re.sub(r"\.\d+", "", info.get("effectiveTime") or "").replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def _agg(level: str, interval: str) -> dict:
    """Tier aggregation: one tier ladder per billing account or per project, reset monthly or daily."""
    return {"scope": "project" if "PROJECT" in (level or "") else "account",
            "days": HOURS_PER_MONTH_CATALOG / 24 if "DAILY" in (interval or "") else 1.0}


def _rate(sku: dict):
    """Normalised price of a Catalog SKU, from the latest pricingInfo already in effect, or None.

    {"unit": usageUnit, "tiers": [(startUsageAmount, price per usageUnit)], "base": baseUnit,
     "conv": baseUnits per usageUnit, "scope", "days", "api": False}.
    displayQuantity is for display only and is not used.
    """
    now = datetime.now(timezone.utc)
    infos = [(_when(i), n, i) for n, i in enumerate(sku.get("pricingInfo") or []) if isinstance(i, dict)]
    infos = [t for t in infos if t[0] <= now]  # future prices are not in effect yet
    if not infos:
        return None
    info = max(infos, key=lambda t: t[:2])[2]  # newest effectiveTime (later entry on a tie)
    expr = info.get("pricingExpression") or {}
    try:
        tiers = sorted((float(t.get("startUsageAmount") or 0), _money(t.get("unitPrice") or {}))
                       for t in expr.get("tieredRates") or [])
        conv = float(expr.get("baseUnitConversionFactor") or 0)
    except (TypeError, ValueError):
        return None
    if not tiers:
        return None
    agg = info.get("aggregationInfo") or {}
    return {"unit": expr.get("usageUnit", ""), "tiers": tiers, "base": expr.get("baseUnit", ""), "conv": conv,
            **_agg(agg.get("aggregationLevel"), agg.get("aggregationInterval")), "api": False}


def _rate_api(d: dict):
    """Normalised price from a Pricing API (v1beta) answer; also accepts a Catalog-format SKU."""
    if "pricingInfo" in d:
        return _rate(d)
    for p in d.get("prices") or [d]:
        rate = p.get("rate") or {}
        info = rate.get("unitInfo") or {}
        try:
            q = float((info.get("unitQuantity") or {}).get("value") or 1) or 1.0  # listPrice is per unitQuantity units
            tiers = sorted((float((t.get("startAmount") or {}).get("value") or 0), _money(t.get("listPrice") or {}) / q)
                           for t in rate.get("tiers") or [])
        except (TypeError, ValueError):
            continue
        if tiers:
            agg = rate.get("aggregationInfo") or {}
            return {"unit": info.get("unit", ""), "tiers": tiers, "base": "", "conv": 0.0,
                    **_agg(agg.get("level"), agg.get("interval")), "api": True}
    return None


def _price_api(sku_id: str, key: str):
    """Pricing API price of one SKU (cached; None if unavailable)."""
    hit = _price_cache.get(sku_id)
    if hit and time.time() - hit[0] < CACHE_TTL:
        return hit[1]
    try:
        rate = _rate_api(_get(f"/skus/{sku_id}/price", key, {"currencyCode": "USD"}, base=PRICE_API)) if sku_id else None
    except Exception:  # not enabled for this key / network: treat as no price
        rate = None
    with _lock:
        _price_cache[sku_id] = (time.time(), rate)
    return rate


def _dim(unit: str):
    """(dimension, size in bytes/seconds) of a Cloud Billing unit, e.g. "GiBy.h" -> (("By", "t"), 2**30 * 3600)."""
    if not unit:
        return ("?",), 1.0  # missing unit converts to nothing
    dims, size = [], 1.0
    for part in unit.split("."):
        if part in _BYTES:
            dims.append("By"); size *= _BYTES[part]
        elif part in _TIME:
            dims.append("t"); size *= 3600 / _TIME[part]
        elif part not in ("count", "1", ""):
            dims.append(part)  # unknown unit: only converts to itself
    return tuple(sorted(dims)), size


def _factor(rate: dict, unit: str):
    """How many of the SKU's usageUnits make one `unit`, or None if the SKU is billed in another dimension
    (e.g. a per GiB-hour price is never read as a per hour price)."""
    if rate["unit"] == unit:
        return 1.0
    want, have = _dim(unit), _dim(rate["unit"])
    if want[0] == have[0]:
        return want[1] / have[1]
    if rate["base"] and rate["conv"] > 0:  # via baseUnit: conv baseUnits = one usageUnit
        base = _dim(rate["base"])
        if base[0] == want[0]:
            return want[1] / base[1] / rate["conv"]
    return None


def _tiered(rate: dict) -> bool:
    return len(rate["tiers"]) > 1 or rate["tiers"][0][0] > 0


def _ladder(tiers: list, amount: float) -> float:
    """Progressive tiers: each usage range is charged at its own rate."""
    cost = 0.0
    for i, (start, price) in enumerate(tiers):
        if amount <= start:
            break
        end = tiers[i + 1][0] if i + 1 < len(tiers) else amount
        cost += (min(amount, end) - start) * price
    return cost


def tiered_monthly(p: dict, amounts: dict) -> dict:
    """Monthly cost per environment for a tiered price dict; amounts are in the row's cost unit
    (unit-hours for hour/shape, unit-months for month, usage units for usage).
    Account-level tiers are shared by all environments (cost split by share); project-level tiers
    apply to each environment on its own (one project per environment)."""
    out = {e: 0.0 for e in amounts}
    for part in p["tiered"]:
        use = {e: a * part["f"] for e, a in amounts.items()}  # in the SKU's billing unit
        days = part["days"]
        if part["scope"] == "account":
            tot = sum(use.values())
            cost = _ladder(part["tiers"], tot / days) * days
            for e in use:
                out[e] += cost * use[e] / tot if tot else 0.0
        else:
            for e in use:
                out[e] += _ladder(part["tiers"], use[e] / days) * days
    return {e: round(v, 2) for e, v in out.items()}


def _best(skus: list, region: str, *, target: tuple, req=(), any_kw=(), not_kw=(), want=frozenset(), key: str = "", bad_ok=()):
    """Best matching on-demand SKU for this region, priced per cost unit.

    target = (Cloud Billing unit, how many of it make one cost unit), e.g. ("GiBy.h", 1) or ("count", 1e6).
    A SKU that shares no wanted token with the request is not used (no price beats a wrong one).
    The Pricing API is asked only when a candidate's catalog entry has no usable price.
    Returns dict or None.
    """
    cands = []
    for sku in skus:
        cat = sku.get("category", {})
        if cat.get("usageType") != "OnDemand":
            continue
        regions = sku.get("serviceRegions", [])
        if region not in regions and "global" not in regions:
            continue
        desc = sku.get("description", "")
        toks = _tok(desc)
        low = desc.lower()
        if (_BAD.search(low) and not any(w in low for w in bad_ok)) or any(r not in toks for r in req):
            continue
        if any_kw and not (toks & set(any_kw)):
            continue
        if toks & set(not_kw):
            continue
        have = toks | _tok(cat.get("resourceGroup", "")) | _tok(cat.get("resourceFamily", ""))
        # a word of 4+ letters also matches as a prefix ("cluster" ~ "Clusters", "managed" ~ "ManagedZone")
        score = sum(1 for w in want if w in have or (len(w) >= 4 and any(t.startswith(w) for t in have)))
        if score == 0 and not (req or any_kw):  # no wanted, required or kind token in common: unrelated
            continue
        cands.append(((score, region in regions, -len(desc)), sku))  # exact region beats "global" at equal score
    api_calls = 0
    for (score, _, _), sku in sorted(cands, key=lambda c: c[0], reverse=True):
        rate = _rate(sku)
        if rate is None and key and api_calls < 3:
            api_calls += 1
            rate = _price_api(sku.get("skuId", ""), key)
        if not rate or not any(p > 0 for _, p in rate["tiers"]):
            continue
        f = _factor(rate, target[0])
        if f is None:
            continue
        f *= target[1]
        paid = next(p for _, p in rate["tiers"] if p > 0)
        return {"price": paid * f, "f": f, "rate": rate, "desc": sku.get("description", ""), "score": score, "api": rate["api"]}
    return None


def _src(m: dict) -> str:
    s = "gcp-catalog" if m["score"] >= 1 else "gcp-catalog (low match - verify)"
    return s + (" + pricing API" if m.get("api") else "")


def _done(p: dict, ms: list, label: str) -> dict:
    """Add source / SKU description and, for tiered SKUs, the tier ladders tiered_monthly() needs."""
    p["source"] = _src({"score": min(m["score"] for m in ms), "api": any(m["api"] for m in ms)})
    p["sku_desc"] = " + ".join(m["desc"] for m in ms)
    if any(_tiered(m["rate"]) for m in ms):
        p["tiered"] = [{"tiers": m["rate"]["tiers"], "f": m["f"], "scope": m["rate"]["scope"], "days": m["rate"]["days"]}
                       for m in ms]
        texts = []
        for m in ms:
            steps = ", ".join(f"{a / m['f']:,.6g}+ @ ${pr * m['f']:.6g}" for a, pr in m["rate"]["tiers"])
            scope = ("per project" if m["rate"]["scope"] == "project" else "per billing account") + \
                    (" per day" if m["rate"]["days"] > 1 else " per month")
            texts.append((m["desc"] + ": " if len(ms) > 1 else "") + f"{steps} per {label} ({scope})")
        p["tier_text"] = "; ".join(texts)
        p["price_text"] += " (tiered)"
    return p


def _static(item: dict, s: dict, reason: str) -> dict:
    mode = s["mode"]
    # a price taken from a public GCP list-price page names that page; otherwise it is an approximation
    src = f"web list price ({s['web']})" if s.get("web") else f"static (approx; {reason})"
    unit = s["unit"]
    basis = s["plabel"] or f"per {unit}"
    if s.get("free"):
        return {"mode": "free", "source": "free", "sku_desc": "", "unit_hr": 0.0, "unit_month": 0.0, "price_text": "Free"}
    if s["static"] is None and mode in ("hour", "month", "usage"):  # no list price: cells stay empty, out of totals
        no = "no fixed list price" if not s["catalog"] else f"no price found ({reason})"
        return {"mode": "usage", "source": no, "sku_desc": "", "usage_price": None, "price_text": basis}
    if mode == "hour":
        return {"mode": mode, "source": src, "sku_desc": "", "unit_hr": s["static"], "price_text": f"${s['static']:.4f} / {unit}-hr"}
    if mode == "shape":
        v, r = _dims(item, s)
        hr = v * s["static_cpu"] + r * s["static_ram"]
        return {"mode": mode, "source": src, "sku_desc": "", "unit_hr": hr, "price_text": f"${hr:.4f} / {unit}-hr ({v:g} vCPU, {r:g} GiB)"}
    if mode == "month":
        return {"mode": mode, "source": src, "sku_desc": "", "unit_month": s["static"], "price_text": f"${s['static']:.2f} / {unit}-month"}
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
    # a count unit of "GB" (e.g. Memorystore capacity) is billed per GiB-hour, everything else per unit-hour
    per_unit = "GiBy." if unit == "GB" else ""
    if mode == "hour":
        m = _best(skus, region, target=(per_unit + "h", 1), req=s["req"], not_kw=s["excl"], want=want, key=key)
        if not m:
            return None
        hr = m["price"]
        return _done({"mode": mode, "unit_hr": hr, "price_text": f"${hr:.4f} / {unit}-hr"}, [m], f"{unit}-hr")
    if mode == "shape":
        shape = s["shape"]
        want |= set(_SHAPE_PREF.get(shape, ()))
        if shape == "cloudsql":  # AlloyDB has no zonal / regional SKU split
            want |= {"regional"} if "ha" in item["sku_tier"].lower().split() or "ha" in _tok(item["sku_tier"]) else {"zonal"}
        ex = set(_SHAPE_EXCL.get(shape, ()))
        cpu = _best(skus, region, target=("h", 1), any_kw=_CPU, not_kw=set(_RAM) | ex, want=want, key=key)  # per vCPU-hour
        ram = _best(skus, region, target=("GiBy.h", 1), any_kw=_RAM, not_kw=ex, want=want, key=key)  # per GiB-hour
        if not cpu or not ram:
            return None
        v, r = _dims(item, s)
        hr = v * cpu["price"] + r * ram["price"]
        cpu["f"] *= v  # SKU units per instance-hour
        ram["f"] *= r
        return _done({"mode": mode, "unit_hr": hr, "price_text": f"${hr:.4f} / {unit}-hr ({v:g} vCPU, {r:g} GiB)"},
                     [cpu, ram], f"{unit}-hr")
    if mode == "month":
        kw = dict(req=s["req"], not_kw=s["excl"], want=want, key=key, bad_ok=s.get("bad_ok", ()))
        m = _best(skus, region, target=(per_unit + "mo", 1), **kw)
        if not m and s.get("count_month"):  # SKU billed per count (a licence / job-day) where count_month of them make one month
            m = _best(skus, region, target=("count", s["count_month"]), **kw)
        if not m:
            return None
        pm = m["price"]
        return _done({"mode": mode, "unit_month": pm, "price_text": f"${pm:.2f} / {unit}-month"}, [m], f"{unit}-month")
    per = USAGE_UNITS.get(s["plabel"])  # usage: price must be convertible to the unit the LLM estimates volume in
    if not per:
        return None
    if s.get("ha_aware"):  # replicated (HA) databases use the Regional storage SKU, others the Zonal one
        want |= {"regional"} if "ha" in _tok(item["sku_tier"]) else {"zonal"}
    req, excl = list(s["req"]), list(s["excl"])
    if s["plabel"].endswith("tokens") and "gemini" in item["sku_tier"].lower():  # Flash vs Flash-Lite are different SKUs
        (req if "lite" in _tok(item["sku_tier"]) else excl).append("lite")
    kw = dict(target=per, req=req, not_kw=excl, want=want, key=key, bad_ok=s.get("bad_ok", ()))
    if s.get("tier_any"):  # every word of the model / data type in sku_tier must be in the SKU: another model's price is never used
        words = _tok(item["sku_tier"]) - _TIER_NOISE
        if not words:
            return None
        kw["req"] = req + sorted(words)
    # version numbers in the tier (e.g. "Gemini 2.5 Flash") must match too; _tok ignores digits
    ver = re.findall(r"\d+(?:\.\d+)*", item["sku_tier"])
    same = [k for k in skus if all(re.search(rf"(?<![\d.]){re.escape(v)}(?![\d.])", k.get("description", "")) for v in ver)]
    m = _best(same, region, **kw) if ver else None
    if not m:
        m = _best(skus, region, **kw)
        if m and ver:
            m["score"] = 0  # requested version not in any SKU: shown as "low match - verify"
    if not m:
        return None
    return _done({"mode": "usage", "usage_price": m["price"], "price_text": f"${m['price']:.6g} {s['plabel']}"},
                 [m], s["plabel"][4:])


def price_items(items: list) -> list:
    """items: dicts with service, sku_tier, region, vcpu, ram_gb. Returns one price dict per item.
    A live price dict for a tiered SKU also has "tiered" / "tier_text" (cost it with tiered_monthly())."""
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
