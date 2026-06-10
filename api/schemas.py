from typing import Optional, List
from pydantic import BaseModel, Field


class TextAnalysisRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=5,
        max_length=10000,
        description="Message or transcript to analyse"
    )
    explain: bool = Field(
        default=False,
        description="Include SHAP token explanations"
    )


class TokenExplanation(BaseModel):
    token: str
    shap_value: float
    direction: str


class AnalysisResponse(BaseModel):
    risk_score: float
    risk_level: str
    risk_color: str
    flags: List[str]
    text_score: float
    audio_score: Optional[float] = None
    top_tokens: Optional[List[TokenExplanation]] = None
    disclaimer: str