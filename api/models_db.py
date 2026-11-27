from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(80), default="")
    role: Mapped[str] = mapped_column(String(20), default="user")  # user | counsellor
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Consent + support settings
    trusted_contact_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    trusted_contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    share_with_counsellor: Mapped[bool] = mapped_column(Boolean, default=False)
    save_text_default: Mapped[bool] = mapped_column(Boolean, default=True)
    comfort_kit: Mapped[list] = mapped_column(JSON, default=list)

    checkins = relationship("CheckIn", back_populates="user", cascade="all, delete-orphan")
    journal = relationship("JournalEntry", back_populates="user", cascade="all, delete-orphan")
    questionnaires = relationship("QuestionnaireResult", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("ComfortActivity", back_populates="user", cascade="all, delete-orphan")


class CheckIn(Base):
    __tablename__ = "checkins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    mood: Mapped[str | None] = mapped_column(String(20), nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)  # only if user allows
    transcript_used: Mapped[bool] = mapped_column(Boolean, default=False)
    has_audio: Mapped[bool] = mapped_column(Boolean, default=False)
    text_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    audio_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(12))
    crisis_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    top_words: Mapped[list] = mapped_column(JSON, default=list)
    audio_stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    feedback: Mapped[str | None] = mapped_column(String(10), nullable=True)  # yes | no
    review_status: Mapped[str] = mapped_column(String(20), default="new")  # counsellor workflow

    user = relationship("User", back_populates="checkins")


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    mood: Mapped[str | None] = mapped_column(String(20), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    crisis_detected: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="journal")


class QuestionnaireResult(Base):
    __tablename__ = "questionnaire_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    kind: Mapped[str] = mapped_column(String(10))  # phq9 | gad7
    answers: Mapped[list] = mapped_column(JSON)
    score: Mapped[int] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(30))

    user = relationship("User", back_populates="questionnaires")


class ComfortActivity(Base):
    __tablename__ = "comfort_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    kind: Mapped[str] = mapped_column(String(30))  # breathing | sound | release | grounding
    detail: Mapped[str | None] = mapped_column(String(60), nullable=True)
    minutes: Mapped[float] = mapped_column(Float, default=0)

    user = relationship("User", back_populates="activities")
