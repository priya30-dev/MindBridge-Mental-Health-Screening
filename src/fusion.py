import numpy as np

TEXT_WEIGHT = 0.65
AUDIO_WEIGHT = 0.35

RISK_LEVELS = {
    (0, 30): ("LOW", "#22C55E"),
    (30, 60): ("MEDIUM", "#F59E0B"),
    (60, 80): ("HIGH", "#F97316"),
    (80, 100): ("CRITICAL", "#EF4444"),
}


def fuse_scores(text_score, audio_score=None):
    if audio_score is not None:
        combined = TEXT_WEIGHT * text_score + AUDIO_WEIGHT * audio_score
    else:
        combined = text_score

    combined = float(np.clip(combined, 0, 100))

    level = "LOW"
    color = "#22C55E"

    for (lo, hi), (lv, col) in RISK_LEVELS.items():
        if lo <= combined < hi or (hi == 100 and combined == 100):
            level = lv
            color = col
            break

    flags = []

    if combined >= 80:
        flags.append("IMMEDIATE_REVIEW_REQUIRED")

    if combined >= 60:
        flags.append("CLINICAL_CONSULTATION_ADVISED")

    if combined >= 30:
        flags.append("MONITORING_RECOMMENDED")

    return {
        "risk_score": round(combined, 2),
        "risk_level": level,
        "risk_color": color,
        "flags": flags,
        "text_score": round(text_score, 2),
        "audio_score": round(audio_score, 2) if audio_score is not None else None,
        "disclaimer": (
            "This is an algorithmic alert, not a clinical diagnosis. "
            "A qualified mental health professional should review all flagged cases."
        ),
    }


if __name__ == "__main__":
    print(fuse_scores(75, 60))