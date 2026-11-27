import os
import tempfile
from datetime import timedelta

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from api import services
from api.db import get_db
from api.models_db import CheckIn, User, utcnow
from api.security import get_current_user

router = APIRouter()

ALLOWED_EXTS = {".wav", ".mp3", ".ogg", ".flac", ".m4a", ".webm"}
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MOODS = {"thriving", "okay-ish", "meh", "stressed", "low"}


def checkin_out(c: CheckIn) -> dict:
    return {
        "id": c.id, "created_at": c.created_at.isoformat(), "mood": c.mood, "text": c.text,
        "has_audio": c.has_audio, "transcript_used": c.transcript_used,
        "text_score": c.text_score, "audio_score": c.audio_score,
        "risk_score": c.risk_score, "risk_level": c.risk_level,
        "crisis_detected": c.crisis_detected, "top_words": c.top_words or [], "feedback": c.feedback,
    }


@router.post("")
async def create_checkin(
    text: str = Form(default=""),
    mood: str = Form(default=""),
    explain: bool = Form(default=True),
    save_text: bool | None = Form(default=None),
    audio: UploadFile | None = File(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    text = text.strip()
    if len(text) > 10000:
        raise HTTPException(422, "Text is too long (max 10,000 characters)")
    if not text and audio is None:
        raise HTTPException(422, "Type something or add a voice note")
    if mood and mood not in MOODS:
        raise HTTPException(422, f"mood must be one of {sorted(MOODS)}")

    if not text and audio is not None and not services.voice_model_ready() and not services.transcription_enabled():
        raise HTTPException(422, "Voice-only check-ins aren't available yet on this server — "
                                 "please type a few words with your voice note.")

    audio_part, stats, transcript_used, tmp_path = None, None, False, None
    try:
        if audio is not None:
            ext = os.path.splitext(audio.filename or "voice.wav")[-1].lower() or ".wav"
            if ext not in ALLOWED_EXTS:
                raise HTTPException(400, f"Unsupported audio format. Use: {sorted(ALLOWED_EXTS)}")
            content = await audio.read()
            if len(content) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "Audio too large (max 25 MB)")
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            audio_part = services.analyse_audio(tmp_path)
            stats = audio_part["stats"]
            if not text:
                transcript = services.transcribe(tmp_path)
                if transcript:
                    text, transcript_used = transcript, True
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    voice_scored = audio_part is not None and audio_part["audio_score"] is not None
    if not text and not voice_scored:
        raise HTTPException(422, "Voice-only check-ins aren't available yet on this server — "
                                 "please type a few words with your voice note.")

    text_part = None
    if text:
        if len(text) < 3:
            raise HTTPException(422, "Write a little more so we can understand")
        try:
            text_part = services.analyse_text(text, explain=explain)
        except services.ModelUnavailable as e:
            raise HTTPException(503, str(e))

    report = services.combine(text_part, audio_part if voice_scored else None)

    # Voice cues vs this user's own baseline
    cues = None
    if stats:
        past = db.scalars(
            select(CheckIn.audio_stats).where(CheckIn.user_id == user.id, CheckIn.audio_stats.is_not(None))
            .order_by(CheckIn.created_at.desc()).limit(20)
        ).all()
        cues = services.audio_cues(stats, [p for p in past if p])

    keep_text = user.save_text_default if save_text is None else save_text
    checkin = CheckIn(
        user_id=user.id, mood=mood or None, text=text if (keep_text and text) else None,
        transcript_used=transcript_used, has_audio=audio_part is not None,
        text_score=report["text_score"], audio_score=report["audio_score"],
        risk_score=report["risk_score"], risk_level=report["risk_level"],
        crisis_detected=report["crisis_detected"],
        top_words=text_part["top_words"] if text_part else [], audio_stats=stats,
    )
    db.add(checkin)
    db.commit()

    recent = db.scalars(
        select(CheckIn.risk_score).where(CheckIn.user_id == user.id)
        .order_by(CheckIn.created_at.desc()).limit(7)
    ).all()[::-1]

    suggest_contact = None
    if (report["crisis_detected"] or report["risk_score"] >= 80) and user.trusted_contact_phone:
        suggest_contact = {"name": user.trusted_contact_name, "phone": user.trusted_contact_phone}

    return {
        **report,
        "id": checkin.id,
        "created_at": checkin.created_at.isoformat(),
        "mood": checkin.mood,
        "analysed_text": text or None,
        "transcript_used": transcript_used,
        "emotion": text_part["emotion"] if text_part else None,
        "probabilities": text_part.get("probabilities") if text_part else None,
        "language_note": text_part.get("language_note") if text_part else None,
        "language": text_part.get("language") if text_part else None,
        "model_used": text_part.get("model_used") if text_part else None,
        "voice_model_ready": services.voice_model_ready(),
        "top_tokens": text_part["top_words"] if text_part else [],
        "voice": cues,
        "trend_alert": services.trend_alert(list(recent)),
        "suggest_contact": suggest_contact,
    }


@router.get("")
def list_checkins(days: int = 30, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = utcnow() - timedelta(days=max(1, min(days, 365)))
    rows = db.scalars(
        select(CheckIn).where(CheckIn.user_id == user.id, CheckIn.created_at >= since)
        .order_by(CheckIn.created_at.desc())
    ).all()
    return [checkin_out(c) for c in rows]


class FeedbackIn(BaseModel):
    feedback: str  # "yes" | "no"


@router.post("/{checkin_id}/feedback")
def feedback(checkin_id: int, body: FeedbackIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.feedback not in ("yes", "no"):
        raise HTTPException(422, "feedback must be 'yes' or 'no'")
    c = db.get(CheckIn, checkin_id)
    if not c or c.user_id != user.id:
        raise HTTPException(404, "Check-in not found")
    c.feedback = body.feedback
    db.commit()
    return {"ok": True}
