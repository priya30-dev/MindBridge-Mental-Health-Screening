"""Counsellor view: only check-ins from users who opted in, pseudonymised.
Counsellor accounts are set with COUNSELLOR_EMAILS in .env."""

import hashlib
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.db import get_db
from api.models_db import CheckIn, User, utcnow
from api.security import SECRET_KEY, require_counsellor

router = APIRouter()
STATUSES = ("new", "reviewed", "contacted", "resolved")


def alias(user_id: int) -> str:
    return "student-" + hashlib.sha256(f"{SECRET_KEY}:{user_id}".encode()).hexdigest()[:6]


@router.get("/flagged")
def flagged(days: int = 14, min_risk: float = 60, _: User = Depends(require_counsellor), db: Session = Depends(get_db)):
    since = utcnow() - timedelta(days=max(1, min(days, 90)))
    rows = db.execute(
        select(CheckIn, User).join(User, CheckIn.user_id == User.id)
        .where(User.share_with_counsellor.is_(True), CheckIn.created_at >= since,
               (CheckIn.risk_score >= min_risk) | CheckIn.crisis_detected.is_(True))
        .order_by(CheckIn.crisis_detected.desc(), CheckIn.risk_score.desc())
    ).all()
    return [{"id": c.id, "student": alias(u.id), "created_at": c.created_at.isoformat(),
             "risk_score": c.risk_score, "risk_level": c.risk_level, "crisis_detected": c.crisis_detected,
             "mood": c.mood, "status": c.review_status} for c, u in rows]


class StatusIn(BaseModel):
    status: str


@router.patch("/flagged/{checkin_id}")
def set_status(checkin_id: int, body: StatusIn, _: User = Depends(require_counsellor), db: Session = Depends(get_db)):
    if body.status not in STATUSES:
        raise HTTPException(422, f"status must be one of {STATUSES}")
    c = db.get(CheckIn, checkin_id)
    if not c or not c.user.share_with_counsellor:
        raise HTTPException(404, "Not found")
    c.review_status = body.status
    db.commit()
    return {"ok": True}
