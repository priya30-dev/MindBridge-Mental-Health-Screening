import os
import sys
import tempfile

from fastapi import APIRouter, UploadFile, File, HTTPException

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "src"))
sys.path.append(SRC_DIR)

from api.schemas import AnalysisResponse
from src.audio_model import predict_audio_features
from src.fusion import fuse_scores
from src.utils import extract_audio_features
router = APIRouter()

ALLOWED_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}


@router.post("/analyse", response_model=AnalysisResponse)
async def analyse_audio(file: UploadFile = File(...)):
    from api.main import models

    ext = os.path.splitext(file.filename or "")[-1].lower()

    if ext not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Use: {ALLOWED_EXTS}"
        )

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        audio_features = extract_audio_features(tmp_path)

        audio_result = predict_audio_features(
            audio_features,
            models["audio_model"],
            models["audio_scaler"]
        )

        audio_score = audio_result["risk_score"]

        fusion_result = fuse_scores(
            text_score=audio_score,
            audio_score=None
        )

        return AnalysisResponse(
            risk_score=fusion_result["risk_score"],
            risk_level=fusion_result["risk_level"],
            risk_color=fusion_result["risk_color"],
            flags=fusion_result["flags"],
            text_score=fusion_result["text_score"],
            audio_score=audio_score,
            top_tokens=None,
            disclaimer=fusion_result["disclaimer"],
        )

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)