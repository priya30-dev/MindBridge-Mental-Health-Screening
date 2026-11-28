import os
import sys
import tempfile

from fastapi import APIRouter, UploadFile, File, HTTPException

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", "src"))
sys.path.append(SRC_DIR)

from api.schemas import AnalysisResponse
from src.fusion import fuse_scores

router = APIRouter()

ALLOWED_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB, matches the dashboard limit


@router.post("/analyse", response_model=AnalysisResponse)
async def analyse_audio(file: UploadFile = File(...)):
    from api.state import models

    if "audio_model" not in models:
        raise HTTPException(status_code=503, detail="The voice model isn't loaded on this server.")

    ext = os.path.splitext(file.filename or "")[-1].lower()

    if ext not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Use: {ALLOWED_EXTS}"
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 25 MB)")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Imported here so the server starts even without the optional voice-model packages
        from src.audio_model import predict_audio_features
        from src.utils import extract_audio_features

        audio_features = extract_audio_features(tmp_path)

        audio_result = predict_audio_features(
            audio_features,
            models["audio_model"],
            models["audio_scaler"]
        )

        audio_score = audio_result["risk_score"]

        # Audio-only request: score goes in the audio slot, not the text slot
        fusion_result = fuse_scores(
            text_score=None,
            audio_score=audio_score,
        )

        return AnalysisResponse(**fusion_result, top_tokens=None)

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)