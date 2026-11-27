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
    mood: Optional[str] = Field(
        default=None,
        description="Self-reported mood from the dashboard (optional)"
    )


class TokenExplanation(BaseModel):
    token: str
    shap_value: float
    direction: str


class CrisisResource(BaseModel):
    name: str
    contact: str
    hours: str


class AnalysisResponse(BaseModel):
    risk_score: float
    risk_level: str
    risk_color: str
    flags: List[str]
    text_score: Optional[float] = None
    audio_score: Optional[float] = None
    top_tokens: Optional[List[TokenExplanation]] = None
    crisis_detected: bool = False
    crisis_resources: Optional[List[CrisisResource]] = None
    demo_mode: bool = False
    disclaimer: str
