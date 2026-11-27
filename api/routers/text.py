from fastapi import APIRouter, HTTPException

from api import services
from api.schemas import AnalysisResponse, TextAnalysisRequest, TokenExplanation

router = APIRouter()


@router.post("/analyse", response_model=AnalysisResponse)
async def analyse_text(req: TextAnalysisRequest):
    """Stateless text analysis (no login, nothing saved)."""
    try:
        part = services.analyse_text(req.text, explain=req.explain)
    except services.ModelUnavailable as e:
        raise HTTPException(503, str(e))

    fusion_result = services.combine(part, None)
    top_tokens = [TokenExplanation(**t) for t in part["top_words"]] if req.explain else None
    return AnalysisResponse(**fusion_result, top_tokens=top_tokens)
