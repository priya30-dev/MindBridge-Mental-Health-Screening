from fastapi import APIRouter, Request

from api.schemas import (
    TextAnalysisRequest,
    AnalysisResponse,
    TokenExplanation,
)

from src.text_model import predict_text
from src.fusion import fuse_scores
from src.explainer import explain_text

router = APIRouter()


def emotion_to_risk(text_result):
    emotion = text_result["emotion"]
    confidence = text_result["confidence"]

    risk_weights = {
        "sadness": 0.85,
        "fear": 0.75,
        "anger": 0.65,
        "surprise": 0.35,
        "love": 0.15,
        "joy": 0.05,
    }

    return round(
        confidence * risk_weights.get(emotion, 0.5),
        2
    )


@router.post(
    "/analyse",
    response_model=AnalysisResponse
)
async def analyse_text(
    req: TextAnalysisRequest,
    request: Request
):
    from api.main import models

    tokenizer = models["tokenizer"]
    text_model = models["text_model"]

    text_result = predict_text(
        req.text,
        tokenizer,
        text_model
    )

    text_score = emotion_to_risk(text_result)

    fusion_result = fuse_scores(
        text_score=text_score,
        audio_score=None
    )

    top_tokens = None

    if req.explain:
        exp = explain_text(
            text=req.text,
            tokenizer=tokenizer,
            model=text_model,
            target_class=text_result["label"]
        )

        top_tokens = [
            TokenExplanation(
                token=item["token"],
                shap_value=item["shap_value"],
                direction=item["direction"]
            )
            for item in exp["top_tokens"]
        ]

    return AnalysisResponse(
        risk_score=fusion_result["risk_score"],
        risk_level=fusion_result["risk_level"],
        risk_color=fusion_result["risk_color"],
        flags=fusion_result["flags"],
        text_score=fusion_result["text_score"],
        audio_score=fusion_result["audio_score"],
        top_tokens=top_tokens,
        disclaimer=fusion_result["disclaimer"],
    )