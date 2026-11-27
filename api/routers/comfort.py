import random

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.db import get_db
from api.models_db import ComfortActivity, User
from api.security import get_current_user

router = APIRouter()

AFFIRMATIONS = [
    "you don't have to have it all figured out today.",
    "rest is productive too.",
    "your feelings are valid, even the messy ones.",
    "one bad day is not a bad life.",
    "you've gotten through every hard day so far.",
    "it's okay to ask for help. that's strength, not weakness.",
    "progress isn't always loud. small steps count.",
    "you are more than your marks, your job, or your follower count.",
    "breathe. this moment will pass.",
    "be as kind to yourself as you'd be to your best friend.",
]

KINDS = {"breathing", "sound", "release", "grounding", "affirmation"}


@router.get("/affirmation")
def affirmation():
    return {"text": random.choice(AFFIRMATIONS)}


class ActivityIn(BaseModel):
    kind: str
    detail: str | None = Field(default=None, max_length=60)
    minutes: float = Field(default=0, ge=0, le=240)


@router.post("/activity")
def log_activity(body: ActivityIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.kind not in KINDS:
        raise HTTPException(422, f"kind must be one of {sorted(KINDS)}")
    # Note: 'release' never stores the worry text itself — only that it happened.
    db.add(ComfortActivity(user_id=user.id, kind=body.kind, detail=body.detail, minutes=body.minutes))
    db.commit()
    return {"ok": True}
