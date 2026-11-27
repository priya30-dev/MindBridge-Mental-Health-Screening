from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.db import get_db
from api.models_db import User
from api.routers.auth import user_out
from api.routers.checkins import checkin_out
from api.routers.journal import entry_out
from api.security import get_current_user

router = APIRouter()


@router.get("/export")
def export_my_data(user: User = Depends(get_current_user)):
    """Everything we store about you, as JSON."""
    return {
        "profile": user_out(user),
        "checkins": [checkin_out(c) for c in user.checkins],
        "journal": [entry_out(e) for e in user.journal],
        "questionnaires": [{"kind": q.kind, "answers": q.answers, "score": q.score,
                            "severity": q.severity, "created_at": q.created_at.isoformat()} for q in user.questionnaires],
        "comfort_activities": [{"kind": a.kind, "detail": a.detail, "minutes": a.minutes,
                                "created_at": a.created_at.isoformat()} for a in user.activities],
    }


@router.delete("")
def delete_my_account(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Permanently deletes the account and all related data."""
    db.delete(user)
    db.commit()
    return {"deleted": True}
