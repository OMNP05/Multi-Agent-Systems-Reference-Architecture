"""Request/response models and the LLM output schema."""
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

ENVS = ["DEV", "SIT", "UAT", "PROD"]

Provider = Literal["openai_compatible", "azure_openai", "anthropic", "gemini"]


class BomRequest(BaseModel):
    use_case: str = Field(min_length=10)
    nfr: str = ""  # non-functional requirements (optional free text)
    provider: Provider
    endpoint: Optional[str] = None  # base URL (OpenAI/Anthropic) or Azure endpoint
    model: str
    api_key: str
    region: str = "asia-south1"


class LlmComponent(BaseModel):
    """One component as returned by the LLM (validated by the graph)."""
    group: Literal["fixed", "nfr"] = "fixed"
    layer: str = ""
    service: str
    sku_tier: str = ""
    logical: str = ""  # logical component from the KB mapping this service realises
    reason: str = ""  # why this GCP service fits the project
    qty_reason: str = ""  # why this instance count per environment
    purpose: str = ""  # what this component does for THIS use case (Pipeline tab)
    build_usage: float = 0  # ONE-TIME build-phase volume in the service's usage unit (e.g. initial document ingestion), not monthly
    vcpu: float = 0
    ram_gb: float = 0
    qty: Dict[str, int]
    usage: Dict[str, float] = Field(default={}, validate_default=True)  # monthly volume per environment, in the service's usage unit (usage-priced services)

    @field_validator("qty")
    @classmethod
    def _qty(cls, v: Dict[str, int]) -> Dict[str, int]:
        out = {e: int(v.get(e, 0)) for e in ENVS}
        if any(n < 0 for n in out.values()):
            raise ValueError("qty must be >= 0")
        return out

    @field_validator("build_usage")
    @classmethod
    def _build(cls, v: float) -> float:
        return max(0.0, float(v or 0))

    @field_validator("usage")
    @classmethod
    def _usage(cls, v: Dict[str, float]) -> Dict[str, float]:
        out = {e: float(v.get(e, 0) or 0) for e in ENVS}
        if any(n < 0 for n in out.values()):
            raise ValueError("usage must be >= 0")
        return out


class LlmBom(BaseModel):
    assumptions: List[str] = []
    mcp_tools: List[str] = []
    layer_purposes: Dict[str, str] = {}  # layer id -> what that layer does for THIS use case
    exclusions: List[str] = []  # what the estimate leaves out (egress, support plan, licences, people...)
    components: List[LlmComponent] = Field(min_length=1)
