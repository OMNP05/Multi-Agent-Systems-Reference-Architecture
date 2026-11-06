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
    hours_per_month: float = 730


class LlmComponent(BaseModel):
    """One component as returned by the LLM (validated by the graph)."""
    group: Literal["fixed", "nfr"] = "fixed"
    layer: str = ""
    service: str
    sku_tier: str = ""
    vcpu: float = 0
    ram_gb: float = 0
    qty: Dict[str, int]

    @field_validator("qty")
    @classmethod
    def _qty(cls, v: Dict[str, int]) -> Dict[str, int]:
        out = {e: int(v.get(e, 0)) for e in ENVS}
        if any(n < 0 for n in out.values()):
            raise ValueError("qty must be >= 0")
        return out


class LlmBom(BaseModel):
    assumptions: List[str] = []
    mcp_tools: List[str] = []
    components: List[LlmComponent] = Field(min_length=1)
