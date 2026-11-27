from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from api import services
from api.db import get_db
from api.models_db import JournalEntry, User, utcnow
from api.security import get_current_user
from src.safety import CRISIS_RESOURCES

router = APIRouter()


class EntryIn(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    mood: str | None = Field(default=None, max_length=20)
    analyse: bool = True


def entry_out(e: JournalEntry) -> dict:
    return {"id": e.id, "created_at": e.created_at.isoformat(), "mood": e.mood,
            "content": e.content, "risk_score": e.risk_score, "crisis_detected": e.crisis_detected}


@router.post("")
def create_entry(body: EntryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    content = body.content.strip()
    risk, crisis = None, False
    if body.analyse and len(content) >= 3 and services.text_model_ready():
        part = services.analyse_text(content, explain=False)
        report = services.combine(part, None)
        risk, crisis = report["risk_score"], report["crisis_detected"]
    else:
        # Safety net always runs, even when analysis is switched off
        from src.safety import detect_crisis_language
        crisis = detect_crisis_language(content)["crisis_detected"]
    entry = JournalEntry(user_id=user.id, content=content, mood=body.mood, risk_score=risk, crisis_detected=crisis)
    db.add(entry)
    db.commit()
    out = entry_out(entry)
    out["crisis_resources"] = CRISIS_RESOURCES if crisis else None
    return out


@router.get("")
def list_entries(days: int = 30, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    since = utcnow() - timedelta(days=max(1, min(days, 365)))
    rows = db.scalars(select(JournalEntry).where(JournalEntry.user_id == user.id, JournalEntry.created_at >= since)
                      .order_by(JournalEntry.created_at.desc())).all()
    return [entry_out(e) for e in rows]


@router.delete("/{entry_id}")
def delete_entry(entry_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    e = db.get(JournalEntry, entry_id)
    if not e or e.user_id != user.id:
        raise HTTPException(404, "Entry not found")
    db.delete(e)
    db.commit()
    return {"ok": True}
