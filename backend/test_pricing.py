"""Offline tests for pricing.py with representative Cloud Billing responses (no live API calls).

Run from backend/:  python -m unittest test_pricing -v
"""
import os
import unittest
from unittest.mock import patch

import httpx

import catalog
import graph
import pricing
from schemas import ENVS


def money(p):
    return {"currencyCode": "USD", "units": str(int(p)), "nanos": int(round((p - int(p)) * 1e9))}


def info(unit, tiers, eff="2024-01-01T00:00:00Z", base="", conv=0, level="ACCOUNT", interval="MONTHLY"):
    """One Catalog pricingInfo entry; tiers = [(startUsageAmount, unit price)]."""
    return {"effectiveTime": eff,
            "pricingExpression": {"usageUnit": unit, "usageUnitDescription": unit, "displayQuantity": 1000,
                                  "baseUnit": base, "baseUnitConversionFactor": conv,
                                  "tieredRates": [{"startUsageAmount": a, "unitPrice": money(p)} for a, p in tiers]},
            "aggregationInfo": {"aggregationLevel": level, "aggregationInterval": interval, "aggregationCount": 1}}


def sku(desc, unit="h", tiers=((0, 0.1),), regions=("us-central1",), sku_id="S-1", infos=None, family="", group="", **kw):
    return {"name": f"services/x/skus/{sku_id}", "skuId": sku_id, "description": desc,
            "category": {"serviceDisplayName": "x", "resourceFamily": family, "resourceGroup": group, "usageType": "OnDemand"},
            "serviceRegions": list(regions), "pricingInfo": infos if infos is not None else [info(unit, tiers, **kw)]}


def row(p, qty, usage=None, usage_unit=None, unit="instance"):
    return {"group": "fixed", "unit": unit, "qty": dict(zip(ENVS, qty)),
            "usage": dict(zip(ENVS, usage or (0, 0, 0, 0))), "usage_unit": usage_unit, "_p": p}


def cost(p, qty, usage=None, usage_unit=None, unit="instance"):
    r = row(p, qty, usage, usage_unit, unit)
    state = {"rows": [r]}
    graph.calculate(state)
    return r


class MockedCatalog(unittest.TestCase):
    """Runs price_items() against mocked catalog SKUs; any real HTTP call fails the test."""

    def setUp(self):
        pricing._price_cache.clear()
        self.patches = [patch.dict(os.environ, {"GCP_PRICING_API_KEY": "test-key"}),
                        patch.object(pricing, "_services", return_value=[]),
                        patch.object(pricing, "_find_service", return_value={"name": "services/x"}),
                        patch.object(pricing, "_get", side_effect=AssertionError("unexpected HTTP call"))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()

    def price(self, service, skus, tier="", region="us-central1", vcpu=0, ram_gb=0):
        with patch.object(pricing, "_skus", return_value=skus):
            return pricing.price_items([{"service": service, "sku_tier": tier, "region": region,
                                         "vcpu": vcpu, "ram_gb": ram_gb}])[0]


class Live(MockedCatalog):
    # 1 -------------------------------------------------------------- single hourly tier
    def test_1_single_hourly_tier(self):
        p = self.price("Google Kubernetes Engine (cluster)", [sku("Regional Kubernetes Clusters management fee", "h", [(0, 0.10)])])
        self.assertEqual(p["source"], "gcp-catalog")
        self.assertAlmostEqual(p["unit_hr"], 0.10)
        self.assertNotIn("tiered", p)
        r = cost(p, (1, 1, 1, 2), unit="cluster")
        self.assertEqual(r["monthly_total"], 5 * 730 * 0.10)
        self.assertIn("5 cluster(s) x 730 h x $0.1000/cluster-hr", r["formula"])

    # 2 -------------------------------------------------------------- multiple progressive tiers
    def test_2_progressive_tiers(self):
        self.assertAlmostEqual(pricing._ladder([(0, 0.08), (10240, 0.06), (153600, 0.04)], 20000),
                               10240 * 0.08 + 9760 * 0.06)
        cdn = sku("Networking Cloud CDN Cache Egress from Americas", "GiBy", [(0, 0.08), (10240, 0.06), (153600, 0.04)])
        p = self.price("Cloud CDN", [cdn])
        self.assertTrue(p["source"].startswith("gcp-catalog"))
        self.assertAlmostEqual(p["usage_price"], 0.08)  # first paid rate, shown in price_text
        self.assertIn("(tiered)", p["price_text"])
        # account-level ladder: all environments share it (200 + 19,800 GB = 20,000 GB)
        r = cost(p, (1, 0, 0, 1), usage=(200, 0, 0, 19800), usage_unit="GB egress", unit="origin")
        self.assertAlmostEqual(r["monthly_total"], 10240 * 0.08 + 9760 * 0.06, places=1)
        self.assertNotEqual(r["monthly_total"], round(20000 * 0.08, 2))  # old flat first-tier result
        self.assertIn("tiered", r["formula"])

    # 3 -------------------------------------------------------------- free tier then paid tier
    def test_3_free_tier_then_paid(self):
        logs = sku("Log Volume", "GiBy", [(0, 0.0), (50, 0.50)], level="PROJECT")
        p = self.price("Cloud Logging", [logs])
        self.assertAlmostEqual(p["usage_price"], 0.50)  # zero-price tier is not taken as the price
        # project-level ladder: each environment (project) gets its own 50 GiB free
        r = cost(p, (1, 1, 1, 1), usage=(10, 30, 60, 200), usage_unit="GiB ingested", unit="log bucket")
        self.assertEqual(r["monthly"], {"DEV": 0.0, "SIT": 0.0, "UAT": 5.0, "PROD": 75.0})
        # all tiers free -> no usable price -> unavailable, never $0 by accident
        p = self.price("Cloud Logging", [sku("Log Volume", "GiBy", [(0, 0.0)])])
        self.assertTrue(p["source"].startswith("static"))

    # 4 -------------------------------------------------------------- GiB-hour / compound units
    def test_4_compound_units(self):
        self.assertAlmostEqual(pricing._factor({"unit": "GiBy.mo", "base": "", "conv": 0}, "GiBy.h"), 1 / 730)
        self.assertAlmostEqual(pricing._factor({"unit": "GiBy.s", "base": "", "conv": 0}, "GiBy.h"), 3600)
        self.assertAlmostEqual(pricing._factor({"unit": "MiBy.h", "base": "", "conv": 0}, "GiBy.h"), 1024)
        self.assertIsNone(pricing._factor({"unit": "GiBy.h", "base": "", "conv": 0}, "h"))  # not a per-hour price
        self.assertIsNone(pricing._factor({"unit": "GiBy.mo", "base": "", "conv": 0}, "By"))  # storage is not egress
        # Memorystore: count unit "GB", SKU per GiB-hour
        p = self.price("Memorystore for Redis", [sku("Redis Capacity Basic M1 Iowa", "GiBy.h", [(0, 0.049)])])
        self.assertAlmostEqual(p["unit_hr"], 0.049)
        # an hour-mode service must not take a GiB-hour SKU as its hourly price
        p = self.price("Cloud Spanner", [sku("Spanner regional node storage", "GiBy.h", [(0, 0.0004)])])
        self.assertTrue(p["source"].startswith("static"))
        self.assertEqual(p["unit_hr"], 0.90)
        # Cloud Run shape: CPU per vCPU-second, memory per GiB-second
        run = [sku("CPU Allocation Time (min instance)", "s", [(0, 0.0000024)], sku_id="C"),
               sku("Memory Allocation Time (min instance)", "GiBy.s", [(0, 0.0000025)], sku_id="M")]
        p = self.price("Cloud Run (min instances)", run, vcpu=1, ram_gb=2)
        self.assertAlmostEqual(p["unit_hr"], 1 * 0.0000024 * 3600 + 2 * 0.0000025 * 3600)

    # 5 -------------------------------------------------------------- usage-based units
    def test_5_usage_units(self):
        skus = [sku("Gemini 2.0 Flash Text Input - Predictions", "count", [(0, 0.15e-6)], sku_id="G20"),
                sku("Gemini 2.5 Flash Text Input - Predictions", "count", [(0, 0.30e-6)], sku_id="G25"),
                sku("Gemini 2.5 Flash Image Input - Predictions", "count", [(0, 0.30e-6)], sku_id="G25I")]
        p = self.price("Vertex AI Gemini (LLM)", skus, tier="Gemini 2.5 Flash")
        self.assertEqual(p["sku_desc"], "Gemini 2.5 Flash Text Input - Predictions")
        self.assertAlmostEqual(p["usage_price"], 0.30)  # per 1M input tokens
        self.assertEqual(p["source"], "gcp-catalog")
        r = cost(p, (1, 0, 0, 1), usage=(5, 0, 0, 200), usage_unit="1M input tokens", unit="model endpoint")
        self.assertEqual(r["monthly_total"], round(205 * 0.30, 2))
        # requested version has no SKU: a sibling price is flagged, not shown as a confident match
        p = self.price("Vertex AI Gemini (LLM)", skus, tier="Gemini 9.9 Flash")
        self.assertEqual(p["source"], "gcp-catalog (low match - verify)")
        # baseUnit conversion: usageUnit "GiBy" priced, base "By", factor 2**30
        logs = sku("Log Volume", "GiBy", [(0, 0.50)], base="By", conv=2 ** 30)
        self.assertAlmostEqual(self.price("Cloud Logging", [logs])["usage_price"], 0.50)
        self.assertAlmostEqual(pricing._factor({"unit": "kcount", "base": "count", "conv": 1000}, "count"), 1 / 1000)

    # 6 -------------------------------------------------------------- several pricingInfo entries
    def test_6_effective_time(self):
        infos = [info("h", [(0, 0.20)], eff="2020-01-01T00:00:00Z"),       # old (index 0 - used to win)
                 info("h", [(0, 0.10)], eff="2025-06-01T08:00:00.123Z"),   # current
                 info("h", [(0, 0.50)], eff="2099-01-01T00:00:00Z")]       # not in effect yet
        p = self.price("Google Kubernetes Engine (cluster)", [sku("Kubernetes Clusters management fee", infos=infos)])
        self.assertAlmostEqual(p["unit_hr"], 0.10)

    # 7 -------------------------------------------------------------- region-specific pricing
    def test_7_region(self):
        skus = [sku("Spanner Instance Node Iowa", "h", [(0, 0.90)], regions=["us-central1"], sku_id="A"),
                sku("Spanner Instance Node Belgium", "h", [(0, 0.99)], regions=["europe-west1"], sku_id="B"),
                sku("Spanner Instance Node", "h", [(0, 1.50)], regions=["global"], sku_id="G")]
        self.assertAlmostEqual(self.price("Cloud Spanner", skus, region="europe-west1")["unit_hr"], 0.99)
        self.assertAlmostEqual(self.price("Cloud Spanner", skus, region="us-central1")["unit_hr"], 0.90)
        self.assertAlmostEqual(self.price("Cloud Spanner", skus, region="asia-south1")["unit_hr"], 1.50)  # global only
        p = self.price("Cloud Spanner", skus[:2], region="asia-south1")  # no SKU for this region
        self.assertTrue(p["source"].startswith("static (approx; no catalog match"))

    # 8 -------------------------------------------------------------- unmatchable SKU
    def test_8_unmatchable(self):
        unrelated = [sku("Backup storage", "h", [(0, 0.02)]), sku("Data transfer out", "h", [(0, 0.12)])]
        p = self.price("Cloud Spanner", unrelated)  # nothing shares "node"/"regional" -> not picked
        self.assertEqual(p["source"], "static (approx; no catalog match)")
        self.assertEqual(p["sku_desc"], "")
        with patch.dict(catalog.CATALOG, {"NoPrice": dict(catalog.CATALOG["Document AI"], static=None, catalog=[], plabel="per widget")}):
            p = self.price("NoPrice", [])  # no list price at all (safety path; the shipped catalogue has no such service)
        self.assertEqual(p["source"], "no fixed list price")
        r = cost(p, (1, 1, 1, 1))
        self.assertIsNone(r["monthly_total"])
        self.assertEqual(r["formula"], "")  # empty, not a placeholder

    # 9 -------------------------------------------------------------- Pricing API down -> fallback
    def test_9_pricing_api(self):
        bare = sku("Spanner Instance Node Iowa", infos=[], sku_id="NOPRICE")  # catalog entry without a price
        down = httpx.HTTPStatusError("403", request=httpx.Request("GET", "u"), response=httpx.Response(403))
        with patch.object(pricing, "_get", side_effect=down) as g:
            p = self.price("Cloud Spanner", [bare])
        self.assertEqual(g.call_args.kwargs["base"], pricing.PRICE_API)
        self.assertEqual(p["source"], "static (approx; no catalog match)")  # labelled static, never live
        self.assertEqual(p["unit_hr"], 0.90)
        # Pricing API up (v1beta format: startAmount / listPrice / unitInfo.unitQuantity)
        pricing._price_cache.clear()
        api = {"name": "skus/NOPRICE/price", "currencyCode": "USD", "valueType": "rate",
               "rate": {"unitInfo": {"unit": "h", "unitDescription": "hour", "unitQuantity": {"value": "10"}},
                        "aggregationInfo": {"level": "LEVEL_ACCOUNT", "interval": "INTERVAL_MONTHLY"},
                        "tiers": [{"startAmount": {"value": "0"}, "listPrice": money(9.0)}]}}
        with patch.object(pricing, "_get", return_value=api):
            p = self.price("Cloud Spanner", [bare])
        self.assertAlmostEqual(p["unit_hr"], 0.90)  # $9 per 10 h
        self.assertEqual(p["source"], "gcp-catalog + pricing API")
        # catalog itself unreachable -> static, labelled as such
        with patch.object(pricing, "_services", side_effect=httpx.ConnectError("down")):
            p = self.price("Cloud Spanner", [bare])
        self.assertEqual(p["source"], "static (approx; catalog error: ConnectError)")


class GcpMethod(MockedCatalog):
    """Input / output tokens, DB storage and one-time build volumes (the Azure sample's method, on GCP)."""

    def test_10_input_output_tokens(self):
        skus = [sku("Gemini 2.5 Flash GA Text Input - Predictions", "count", [(0, 0.30e-6)], sku_id="I", regions=["global"]),
                sku("Gemini 2.5 Flash GA Text Output - Predictions", "count", [(0, 2.5e-6)], sku_id="O", regions=["global"]),
                sku("Gemini 2.5 Flash Lite Text Output - Predictions", "count", [(0, 0.4e-6)], sku_id="OL", regions=["global"])]
        self.assertAlmostEqual(self.price("Vertex AI Gemini (LLM)", skus, tier="Gemini 2.5 Flash")["usage_price"], 0.30)
        out = self.price("Vertex AI Gemini Output (LLM)", skus, tier="Gemini 2.5 Flash")  # "output" must not trip the TPU filter
        self.assertEqual(out["sku_desc"], "Gemini 2.5 Flash GA Text Output - Predictions")
        self.assertAlmostEqual(out["usage_price"], 2.5)
        lite = self.price("Vertex AI Gemini Output (LLM)", skus, tier="Gemini 2.5 Flash-Lite")
        self.assertAlmostEqual(lite["usage_price"], 0.4)
        self.assertTrue(pricing._BAD.search("tpu v5 pod") and not pricing._BAD.search("text output"))

    def test_11_db_storage_follows_ha(self):
        skus = [sku("Cloud SQL for PostgreSQL: Zonal - Standard storage in Mumbai", "GiBy.mo", [(0, 0.204)], regions=["asia-south1"], sku_id="Z"),
                sku("Cloud SQL for PostgreSQL: Regional - Standard storage in Mumbai", "GiBy.mo", [(0, 0.408)], regions=["asia-south1"], sku_id="R"),
                sku("FDC Trial in Cloud SQL for PostgreSQL: Regional - Standard storage in Mumbai", "GiBy.mo", [(0, 0.1)], regions=["asia-south1"], sku_id="F")]
        self.assertAlmostEqual(self.price("Cloud SQL Storage", skus, tier="PostgreSQL, HA", region="asia-south1")["usage_price"], 0.408)
        self.assertAlmostEqual(self.price("Cloud SQL Storage", skus, tier="PostgreSQL", region="asia-south1")["usage_price"], 0.204)

    def test_12_one_time_build_cost(self):
        p = self.price("Document AI", [sku("Document OCR page", "count", [(0, 1.5e-3)])])
        self.assertAlmostEqual(p["usage_price"], 1.5)  # per 1K pages
        r = row(p, (0, 0, 0, 1), usage=(0, 0, 0, 8), usage_unit="1K pages")
        r["build_usage"] = 25  # 25K pages loaded once
        state = {"rows": [r]}
        out = graph.calculate(state)
        self.assertEqual(r["monthly_total"], 12.0)      # 8K pages a month
        self.assertEqual(r["one_time"], 37.5)           # 25K pages once
        self.assertEqual(out["totals"]["ALL"], 12.0)    # one-time is NOT in the monthly total
        self.assertEqual(out["totals"]["ONE_TIME"], 37.5)
        # no build volume -> no one-time cost
        r2 = cost(p, (0, 0, 0, 1), usage=(0, 0, 0, 8), usage_unit="1K pages")
        self.assertIsNone(r2["one_time"])


class PublicPrice(MockedCatalog):
    """Products with no matching live SKU use the public GCP list-price page, and the row says so."""

    def test_13_web_list_price_fallback(self):
        p = self.price("API Gateway", [sku("Network Internet Egress", "GiBy", [(0, 0.12)])])  # egress only: no call SKU
        self.assertEqual(p["source"], "web list price (cloud.google.com/api-gateway/pricing)")
        self.assertAlmostEqual(p["usage_price"], 3.0)
        r = cost(p, (1, 1, 1, 1), usage=(0.5, 0.5, 1, 20), usage_unit="1M API calls", unit="gateway")
        self.assertEqual(r["monthly_total"], 66.0)  # 22M calls a month x $3 per 1M
        # CCAI: the named-user licence SKU is allowed through the licence filter; add-ons are not
        skus = [sku("Contact Center AI Platform usage fees (pay as you go) - named user license per month. ", "mo", [(0, 135.0)], sku_id="N"),
                sku("Contact Center AI Platform add-on subscription fees - Insights - named user license per month.", "mo", [(0, 10.0)], sku_id="I")]
        p = self.price("CCAI Platform", skus)
        self.assertAlmostEqual(p["unit_month"], 135.0)
        self.assertEqual(p["source"], "gcp-catalog")
        # Security Command Center: a month-priced subscription from the public page, not a per-environment SKU
        p = self.price("Security Command Center", [])
        self.assertEqual(p["source"], "web list price (cloud.google.com/security-command-center/pricing)")
        self.assertAlmostEqual(p["unit_month"], 1250.0)


class AnyUseCase(MockedCatalog):
    """Per-model / per-edition services price the named model only, never a neighbour's."""

    GARDEN = [sku("Cloud Vertex AI Model Garden Model as a Service Gemma-4 Input Token", "count", [(0, 1.5e-07)], sku_id="G"),
              sku("Cloud Vertex AI Model Garden Model as a Service Llama 4 Scout Input Tokens", "count", [(0, 2.5e-07)], sku_id="L")]

    def test_14_model_named_in_sku_tier(self):
        p = self.price("Vertex AI Model Garden (LLM)", self.GARDEN, tier="Llama 4 Scout")
        self.assertAlmostEqual(p["usage_price"], 0.25)
        p = self.price("Vertex AI Model Garden (LLM)", self.GARDEN, tier="Mistral Large")  # no such SKU: empty, not Gemma's price
        self.assertIsNone(p["usage_price"])
        self.assertEqual(p["source"], "no price found (no catalog match)")
        p = self.price("Vertex AI Model Garden (LLM)", self.GARDEN, tier="")  # no model named: nothing to match
        self.assertIsNone(p["usage_price"])

    def test_15_editions_and_count_units(self):
        looker = [sku("Looker (Google Cloud core) - Standard Edition", "count", [(0, 5000.0)], sku_id="E"),
                  sku("Looker (Google Cloud core) - Viewer User", "count", [(0, 30.0)], sku_id="V")]
        self.assertAlmostEqual(self.price("Looker", looker, tier="Viewer User")["unit_month"], 30.0)
        self.assertAlmostEqual(self.price("Looker", looker, tier="Standard Edition")["unit_month"], 5000.0)
        job = self.price("Cloud Scheduler", [sku("Jobs", "count", [(0, 0.0), (93, 0.003225806)], regions=("global",))])
        self.assertEqual(job["source"], "gcp-catalog")  # per job-day SKU read as a monthly price (31 days)
        self.assertAlmostEqual(job["tiered"][0]["f"], 31.0)

    def test_16_catalogue_is_consistent(self):
        for name, s in catalog.CATALOG.items():
            self.assertIn(name, catalog.DEFAULT_LAYER, name)
            if s["mode"] == "usage":
                self.assertIn(s["plabel"], catalog.USAGE_UNITS, name)  # volume and price share a unit
            if not s.get("free") and s["static"] is None and s["mode"] != "shape":
                self.assertTrue(s["catalog"], name)  # no static price: it must at least be matchable live
            if s["static"] is not None and not s["catalog"] and not s.get("free"):
                self.assertTrue(s.get("web"), name)  # a price with no live SKU must name its public page


class Formats(unittest.TestCase):
    def test_both_response_formats(self):
        cat = pricing._rate_api(sku("x", "GiBy", [(0, 0.0), (50, 0.5)], level="PROJECT", interval="DAILY"))
        self.assertEqual((cat["unit"], cat["tiers"], cat["scope"], cat["api"]), ("GiBy", [(0, 0.0), (50, 0.5)], "project", False))
        self.assertAlmostEqual(cat["days"], 730 / 24)
        api = pricing._rate_api({"rate": {"unitInfo": {"unit": "GiBy.mo", "unitQuantity": {"value": "1"}},
                                          "tiers": [{"startAmount": {"value": "5"}, "listPrice": money(0.02)},
                                                    {"startAmount": {}, "listPrice": money(0)}]}})
        self.assertEqual((api["unit"], api["tiers"], api["scope"], api["api"]), ("GiBy.mo", [(0, 0.0), (5, 0.02)], "account", True))

    def test_no_key_is_static(self):
        with patch.dict(os.environ, {"GCP_PRICING_API_KEY": ""}):
            p = pricing.price_items([{"service": "Cloud SQL", "sku_tier": "PostgreSQL, HA", "region": "us-central1",
                                      "vcpu": 4, "ram_gb": 16}])[0]
        self.assertEqual(p["source"], "static (approx; set GCP_PRICING_API_KEY for live prices)")
        self.assertAlmostEqual(p["unit_hr"], 4 * 0.0413 + 16 * 0.007)


if __name__ == "__main__":
    unittest.main()
