from pydantic import BaseModel, Field
from typing import List, Optional

class ResourceData(BaseModel):
    resource_type: str = Field(..., description="Indicated 或 Inferred")
    ore_mt: float = Field(..., description="矿石量 (百万吨)")
    grade_au_gt: Optional[float] = Field(None, description="金品位 (g/t)")
    grade_cu_pct: Optional[float] = Field(None, description="铜品位 (%)")
    metal_oz: Optional[float] = Field(None, description="黄金金属量 (盎司)")
    metal_t: Optional[float] = Field(None, description="金属量 (吨)")

class ExtractorOutput(BaseModel):
    company: str = Field(..., description="公司名称")
    resources: List[ResourceData]
    abstain: bool = Field(False, description="是否弃权")
    reasoning: str = Field("", description="弃权或提取理由")