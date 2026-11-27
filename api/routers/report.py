import io
from collections import Counter, defaultdict
from datetime import timedelta
from statistics import mean

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.db import get_db
from api.models_db import CheckIn, ComfortActivity, JournalEntry, QuestionnaireResult, User, utcnow
from api.security import get_current_user

router = APIRouter()

MOOD_ORDER = ["thriving", "okay-ish", "meh", "stressed", "low"]


def build_report(user: User, db: Session, days: int = 30) -> dict:
    days = max(7, min(days, 365))
    now = utcnow()
    since, prev_since = now - timedelta(days=days), now - timedelta(days=2 * days)

    checkins = db.scalars(select(CheckIn).where(CheckIn.user_id == user.id, CheckIn.created_at >= since)
                          .order_by(CheckIn.created_at)).all()
    prev_scores = db.scalars(select(CheckIn.risk_score).where(
        CheckIn.user_id == user.id, CheckIn.created_at >= prev_since, CheckIn.created_at < since)).all()
    activities = db.scalars(select(ComfortActivity).where(
        ComfortActivity.user_id == user.id, ComfortActivity.created_at >= since)).all()
    journal_count = len(db.scalars(select(JournalEntry.id).where(
        JournalEntry.user_id == user.id, JournalEntry.created_at >= since)).all())
    latest_q = {}
    for kind in ("phq9", "gad7"):
        r = db.scalar(select(QuestionnaireResult).where(QuestionnaireResult.user_id == user.id,
                      QuestionnaireResult.kind == kind).order_by(QuestionnaireResult.created_at.desc()))
        if r:
            latest_q[kind] = {"score": r.score, "severity": r.severity, "date": r.created_at.date().isoformat()}

    scores = [c.risk_score for c in checkins]
    by_day = defaultdict(list)
    for c in checkins:
        by_day[c.created_at.date()].append(c.risk_score)
    daily = [{"date": d.isoformat(), "risk": round(mean(v), 1)} for d, v in sorted(by_day.items())]

    moods = Counter(c.mood for c in checkins if c.mood)
    total_moods = sum(moods.values())
    mood_mix = [{"mood": m, "pct": round(100 * moods[m] / total_moods)} for m in MOOD_ORDER if moods[m]] if total_moods else []

    word_counts = Counter()
    for c in checkins:
        for t in c.top_words or []:
            if t.get("direction") == "risk-increasing":
                word = str(t.get("token", "")).strip().lower()
                if len(word) > 2:
                    word_counts[word] += 1
    top_words = [{"word": w, "count": n} for w, n in word_counts.most_common(6)]

    helped = Counter(a.kind for a in activities)
    calm_minutes = round(sum(a.minutes for a in activities if a.kind in ("breathing", "sound")))

    # Insight: next check-in after a breathing day vs other days (needs enough data)
    breathing_days = {a.created_at.date() for a in activities if a.kind == "breathing"}
    insight = None
    after_b, after_other = [], []
    for i in range(1, len(checkins)):
        target = after_b if checkins[i - 1].created_at.date() in breathing_days else after_other
        target.append(checkins[i].risk_score)
    if len(after_b) >= 3 and len(after_other) >= 3:
        diff = mean(after_other) - mean(after_b)
        if diff >= 5:
            insight = "after days you did a breathing session, your next check-in was calmer."
        elif diff <= -5:
            insight = "breathing days didn't line up with calmer check-ins yet — try other tools in the chill zone too."

    best = min(checkins, key=lambda c: c.risk_score) if checkins else None
    return {
        "days": days,
        "period": {"from": since.date().isoformat(), "to": now.date().isoformat()},
        "checkin_count": len(checkins),
        "voice_checkins": sum(1 for c in checkins if c.has_audio),
        "avg_risk": round(mean(scores), 1) if scores else None,
        "prev_avg_risk": round(mean(prev_scores), 1) if prev_scores else None,
        "daily": daily,
        "mood_mix": mood_mix,
        "top_words": top_words,
        "activities": dict(helped),
        "calm_minutes": calm_minutes,
        "journal_entries": journal_count,
        "best_day": {"date": best.created_at.date().isoformat(), "risk": best.risk_score} if best else None,
        "questionnaires": latest_q,
        "insight": insight,
        "high_risk_count": sum(1 for s in scores if s >= 60),
        "disclaimer": "This report shows screening trends, not a diagnosis.",
    }


@router.get("")
def report(days: int = 30, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return build_report(user, db, days)


@router.get("/pdf")
def report_pdf(days: int = 30, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    r = build_report(user, db, days)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title="MindBridge wellness report")
    ss = getSampleStyleSheet()
    purple = colors.HexColor("#4A2FC9")
    h1 = ParagraphStyle("h1", parent=ss["Title"], textColor=purple, alignment=0, fontSize=22)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=colors.HexColor("#1E1B2E"))
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=11, leading=15)
    small = ParagraphStyle("s", parent=body, fontSize=9, textColor=colors.HexColor("#5B5670"))

    story = [Paragraph("MindBridge wellness report", h1),
             Paragraph(f"{user.display_name} · {r['period']['from']} to {r['period']['to']}", body), Spacer(1, 8)]

    def fmt(v):
        return "—" if v is None else str(v)

    change = ""
    if r["avg_risk"] is not None and r["prev_avg_risk"] is not None:
        d = round(r["avg_risk"] - r["prev_avg_risk"], 1)
        change = f" ({'+' if d > 0 else ''}{d} vs previous period)"
    rows = [["Check-ins", fmt(r["checkin_count"]), "With voice", fmt(r["voice_checkins"])],
            ["Average stress (0-100)", fmt(r["avg_risk"]) + change, "High-stress check-ins", fmt(r["high_risk_count"])],
            ["Calm minutes", fmt(r["calm_minutes"]), "Journal entries", fmt(r["journal_entries"])]]
    t = Table(rows, colWidths=[42 * mm, 46 * mm, 42 * mm, 30 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F1FC")),
                           ("FONTSIZE", (0, 0), (-1, -1), 10), ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDD6F5")),
                           ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.white), ("PADDING", (0, 0), (-1, -1), 6)]))
    story += [t, Spacer(1, 10)]

    if len(r["daily"]) >= 2:
        story.append(Paragraph("Stress over time", h2))
        dr = Drawing(170 * mm, 60 * mm)
        lp = LinePlot()
        lp.x, lp.y, lp.width, lp.height = 10 * mm, 8 * mm, 150 * mm, 46 * mm
        lp.data = [[(i, d["risk"]) for i, d in enumerate(r["daily"])]]
        lp.lines[0].strokeColor = purple
        lp.lines[0].strokeWidth = 2
        lp.yValueAxis.valueMin, lp.yValueAxis.valueMax, lp.yValueAxis.valueStep = 0, 100, 20
        lp.xValueAxis.visible = False
        dr.add(lp)
        story += [dr, Paragraph(f"{r['daily'][0]['date']} → {r['daily'][-1]['date']}", small), Spacer(1, 8)]

    if r["mood_mix"]:
        story += [Paragraph("Mood mix", h2),
                  Paragraph(" · ".join(f"{m['mood']} {m['pct']}%" for m in r["mood_mix"]), body)]
    if r["top_words"]:
        story += [Paragraph("What weighed on you", h2),
                  Paragraph(", ".join(f"{w['word']} ({w['count']}×)" for w in r["top_words"]), body)]
    if r["activities"]:
        story += [Paragraph("What you tried", h2),
                  Paragraph(", ".join(f"{k}: {v}" for k, v in r["activities"].items()), body)]
    if r["insight"]:
        story += [Spacer(1, 4), Paragraph(r["insight"], body)]
    if r["questionnaires"]:
        story.append(Paragraph("Questionnaires", h2))
        names = {"phq9": "PHQ-9 (mood, 0-27)", "gad7": "GAD-7 (anxiety, 0-21)"}
        for k, q in r["questionnaires"].items():
            story.append(Paragraph(f"{names[k]}: {q['score']} — {q['severity']} (taken {q['date']})", body))

    story += [Spacer(1, 14), Paragraph(r["disclaimer"] + " If you are in crisis in India, call Tele-MANAS 14416 (24x7, free) or 112.", small)]
    doc.build(story)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/pdf",
                             headers={"Content-Disposition": 'attachment; filename="mindbridge-report.pdf"'})
