import os
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.db import get_db
from api.models_db import User
from api.security import create_token, get_current_user, hash_password, verify_password

router = APIRouter()

COUNSELLOR_EMAILS = {e.strip().lower() for e in os.getenv("COUNSELLOR_EMAILS", "").split(",") if e.strip()}

# Tiny in-memory rate limiter for login/register (per IP): AUTH_RATE_LIMIT attempts / 5 min
_ATTEMPTS: dict[str, deque] = defaultdict(deque)
_WINDOW = 300
_MAX = int(os.getenv("AUTH_RATE_LIMIT", "10"))


def _rate_limit(request: Request):
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    now = time.time()
    q = _ATTEMPTS[ip]
    while q and now - q[0] > _WINDOW:
        q.popleft()
    if len(q) >= _MAX:
        raise HTTPException(429, "Too many attempts. Please wait a few minutes.")
    q.append(now)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=80)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    token: str
    user: dict


class SettingsIn(BaseModel):
    display_name: str | None = Field(default=None, max_length=80)
    trusted_contact_name: str | None = Field(default=None, max_length=80)
    trusted_contact_phone: str | None = Field(default=None, max_length=30)
    share_with_counsellor: bool | None = None
    save_text_default: bool | None = None
    comfort_kit: list[str] | None = Field(default=None, max_length=20)


def user_out(u: User) -> dict:
    return {
        "id": u.id, "email": u.email, "display_name": u.display_name, "role": u.role,
        "trusted_contact_name": u.trusted_contact_name, "trusted_contact_phone": u.trusted_contact_phone,
        "share_with_counsellor": u.share_with_counsellor, "save_text_default": u.save_text_default,
        "comfort_kit": u.comfort_kit or [], "created_at": u.created_at.isoformat(),
    }


@router.post("/register", response_model=TokenOut, dependencies=[Depends(_rate_limit)])
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=email, password_hash=hash_password(body.password),
                display_name=body.display_name.strip() or email.split("@")[0],
                role="counsellor" if email in COUNSELLOR_EMAILS else "user", comfort_kit=[])
    db.add(user)
    db.commit()
    return {"token": create_token(user.id), "user": user_out(user)}


@router.post("/login", response_model=TokenOut, dependencies=[Depends(_rate_limit)])
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Wrong email or password")
    return {"token": create_token(user.id), "user": user_out(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_out(user)


@router.patch("/me")
def update_me(body: SettingsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    return user_out(user)
