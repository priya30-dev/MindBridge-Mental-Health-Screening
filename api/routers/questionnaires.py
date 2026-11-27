"""PHQ-9 (depression) and GAD-7 (anxiety): free, validated screening
questionnaires (Kroenke & Spitzer). Scores are screening aids, not diagnoses."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.db import get_db
from api.models_db import QuestionnaireResult, User
from api.security import get_current_user
from src.safety import CRISIS_RESOURCES

router = APIRouter()

OPTIONS = [
    {"value": 0, "label": "Not at all"},
    {"value": 1, "label": "Several days"},
    {"value": 2, "label": "More than half the days"},
    {"value": 3, "label": "Nearly every day"},
]

QUESTIONNAIRES = {
    "phq9": {
        "title": "PHQ-9 · mood check",
        "prompt": "Over the last 2 weeks, how often have you been bothered by any of the following problems?",
        "items": [
            "Little interest or pleasure in doing things",
            "Feeling down, depressed, or hopeless",
            "Trouble falling or staying asleep, or sleeping too much",
            "Feeling tired or having little energy",
            "Poor appetite or overeating",
            "Feeling bad about yourself — or that you are a failure or have let yourself or your family down",
            "Trouble concentrating on things, such as reading or watching television",
            "Moving or speaking so slowly that other people could have noticed — or being so fidgety or restless that you have been moving around a lot more than usual",
            "Thoughts that you would be better off dead, or of hurting yourself in some way",
        ],
        "bands": [(0, 4, "minimal"), (5, 9, "mild"), (10, 14, "moderate"), (15, 19, "moderately severe"), (20, 27, "severe")],
    },
    "gad7": {
        "title": "GAD-7 · anxiety check",
        "prompt": "Over the last 2 weeks, how often have you been bothered by the following problems?",
        "items": [
            "Feeling nervous, anxious, or on edge",
            "Not being able to stop or control worrying",
            "Worrying too much about different things",
            "Trouble relaxing",
            "Being so restless that it is hard to sit still",
            "Becoming easily annoyed or irritable",
            "Feeling afraid, as if something awful might happen",
        ],
        "bands": [(0, 4, "minimal"), (5, 9, "mild"), (10, 14, "moderate"), (15, 21, "severe")],
    },
}

ADVICE = {
    "minimal": "Looking okay. Keep up the small habits that help you.",
    "mild": "Some signs worth keeping an eye on. Self-care and regular check-ins can help.",
    "moderate": "This is a good time to talk to a counsellor or doctor about how you've been feeling.",
    "moderately severe": "Please consider speaking with a mental health professional soon.",
    "severe": "Please reach out to a mental health professional as soon as you can.",
}


def score_answers(kind: str, answers: list[int]) -> dict:
    q = QUESTIONNAIRES[kind]
    if len(answers) != len(q["items"]) or any(a not in (0, 1, 2, 3) for a in answers):
        raise ValueError(f"{kind} needs {len(q['items'])} answers, each 0-3")
    total = sum(answers)
    severity = next(label for lo, hi, label in q["bands"] if lo <= total <= hi)
    # PHQ-9 item 9 (self-harm thoughts): any non-zero answer needs follow-up
    crisis = kind == "phq9" and answers[8] > 0
    return {"score": total, "max": 3 * len(answers), "severity": severity,
            "advice": ADVICE[severity], "crisis_detected": crisis,
            "crisis_resources": CRISIS_RESOURCES if crisis else None}


@router.get("/{kind}")
def get_questionnaire(kind: str):
    if kind not in QUESTIONNAIRES:
        raise HTTPException(404, "Unknown questionnaire")
    q = QUESTIONNAIRES[kind]
    return {"kind": kind, "title": q["title"], "prompt": q["prompt"], "items": q["items"], "options": OPTIONS}


class AnswersIn(BaseModel):
    answers: list[int]


@router.post("/{kind}")
def submit(kind: str, body: AnswersIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if kind not in QUESTIONNAIRES:
        raise HTTPException(404, "Unknown questionnaire")
    try:
        result = score_answers(kind, body.answers)
    except ValueError as e:
        raise HTTPException(422, str(e))
    db.add(QuestionnaireResult(user_id=user.id, kind=kind, answers=body.answers,
                               score=result["score"], severity=result["severity"]))
    db.commit()
    return result


@router.get("")
def history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(QuestionnaireResult).where(QuestionnaireResult.user_id == user.id)
                      .order_by(QuestionnaireResult.created_at.desc())).all()
    return [{"kind": r.kind, "score": r.score, "severity": r.severity, "created_at": r.created_at.isoformat()} for r in rows]
